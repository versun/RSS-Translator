import logging
import time
import json
from django.utils import timezone
from bs4 import BeautifulSoup
import mistune
import newspaper
from .models import Feed, Entry, AIFilter
from utils.feed_action import fetch_feed, convert_struct_time_to_datetime
from utils import text_handler
from translator.models import TranslatorEngine
from utils.text_handler import get_token_count, adaptive_chunking



def handle_single_feed_fetch(feed: Feed):
    """
    Fetch feeds and update entries with batch processing optimization.
    """
    try:
        feed.fetch_status = None
        fetch_results = fetch_feed(url=feed.feed_url, etag=feed.etag)

        if fetch_results["error"]:
            raise Exception(f"Fetch Feed Failed: {fetch_results['error']}")
        elif not fetch_results["update"]:
            raise Exception("Feed is up to date, Skip")

        latest_feed = fetch_results.get("feed")
        # Update feed meta
        feed.name = latest_feed.feed.get("title") if feed.name is None else feed.name
        feed.subtitle = latest_feed.feed.get("subtitle")
        feed.language = latest_feed.feed.get("language")
        feed.author = latest_feed.feed.get("author") or "Unknown"
        feed.link = latest_feed.feed.get("link") or feed.feed_url
        feed.pubdate = convert_struct_time_to_datetime(
            latest_feed.feed.get("published_parsed")
        )
        feed.updated = convert_struct_time_to_datetime(
            latest_feed.feed.get("updated_parsed")
        )
        feed.last_fetch = timezone.now()
        feed.etag = latest_feed.get("etag")

        # Update entries
        if getattr(latest_feed, "entries", None):
            BATCH_SIZE = 50  # Smaller batch size for memory efficiency
            entries_to_create = []
            existing_entries = dict(
                Entry.objects.filter(feed=feed).values_list("guid", "id")
            )
            
            # Sort entries by publication date (newest first)
            sorted_entries = sorted(
                latest_feed.entries,
                key=lambda x: (
                    x.get("published_parsed") or 
                    x.get("updated_parsed") or 
                    time.gmtime(0)  # Fallback to epoch if no date
                ),
                reverse=True
            )[: feed.max_posts]

            for i, entry_data in enumerate(sorted_entries):
                # Get content
                content = ""
                if "content" in entry_data:
                    content = entry_data.content[0].value or entry_data.content[1].value or ""
                else:
                    content = entry_data.get("summary")

                guid = entry_data.get("id") or entry_data.get("link")
                link = entry_data.get("link", "")
                author = entry_data.get("author", feed.author)
                if not guid:
                    continue  # Skip invalid entries

                # Create new entry if needed
                if guid not in existing_entries:
                    entry_values = {
                        "link": link,
                        "author": author,
                        "pubdate": convert_struct_time_to_datetime(
                            entry_data.get("published_parsed")
                        ),
                        "updated": convert_struct_time_to_datetime(
                            entry_data.get("updated_parsed")
                        ),
                        "original_title": entry_data.get("title", "No title"),
                        "original_content": content,
                        "original_summary": entry_data.get("summary"),
                        "enclosures_xml": entry_data.get("enclosures_xml"),
                    }

                    entries_to_create.append(
                        Entry(feed=feed, guid=guid, **entry_values)
                    )
                    
                    # Batch create periodically
                    if len(entries_to_create) >= BATCH_SIZE:
                        Entry.objects.bulk_create(entries_to_create)
                        entries_to_create = []
                        # Explicitly clear memory
                        del entry_values
                        if 'content' in locals():
                            del content

            # Create remaining entries
            if entries_to_create:
                Entry.objects.bulk_create(entries_to_create)
                del entries_to_create

        feed.fetch_status = True
        feed.log = f"{timezone.now()} Fetch Completed <br>"
    except Exception as e:
        logging.error("Task handle_single_feed_fetch %s: %s", feed.feed_url, str(e))
        feed.fetch_status = False
        feed.log = f"{timezone.now()} {str(e)}<br>"
    finally:
        feed.save()
        # Explicitly clean up large objects
        if 'latest_feed' in locals():
            del latest_feed
        if 'sorted_entries' in locals():
            del sorted_entries
        if 'fetch_results' in locals():
            del fetch_results


def handle_feeds_fetch(feeds: list):
    """
    Fetch feeds and update entries with memory optimization.
    """
    for feed in feeds:
        handle_single_feed_fetch(feed)
        # Explicitly clean up reference
        del feed


def handle_feeds_translation(feeds: list, target_field: str = "title"):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue

            feed.translation_status = None
            logging.info(
                "Start translate %s of feed %s to %s",
                target_field,
                feed.feed_url,
                feed.target_language,
            )

            translate_feed(feed, target_field=target_field)
            feed.translation_status = True
            feed.log += f"{timezone.now()} Translate Completed <br>"
        except Exception as e:
            logging.error(
                "Task handle_feeds_translation (%s)%s: %s",
                feed.target_language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += f"{timezone.now()} {str(e)} <br>"
        finally:
            # Explicitly clean up reference
            del feed

    Feed.objects.bulk_update(
        feeds, fields=["translation_status", "log", "total_tokens", "total_characters"]
    )
    # Clear the list after processing
    del feeds


def handle_feeds_summary(feeds: list):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue

            feed.translation_status = None
            logging.info(
                "Start summary feed %s to %s", feed.feed_url, feed.target_language
            )
            if not feed.summarizer:
                raise Exception("Summarizer Engine Not Set")

            min_chunk_size = feed.summarizer.min_size()
            max_chunk_size = feed.summarizer.max_size()
            max_context_tokens = feed.summarizer.max_tokens

            summarize_feed(feed, min_chunk_size=min_chunk_size, max_chunk_size=max_chunk_size, max_context_tokens=max_context_tokens)
            feed.translation_status = True
            feed.log += f"{timezone.now()} Summary Completed <br>"
        except Exception as e:
            logging.error(
                "Task handle_feeds_summary (%s)%s: %s",
                feed.target_language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += f"{timezone.now()} {str(e)}<br>"
        finally:
            # Explicitly clean up reference
            del feed

    Feed.objects.bulk_update(
        feeds, fields=["translation_status", "log", "total_tokens", "total_characters"]
    )
    # Clear the list after processing
    del feeds


def handle_filtration(feeds: list, digest: AIFilter):
    digest.status = None
    # digest.save()
    logging.info("Digest processing started: %s", digest.name)

    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue

            digest.status = None
            logging.info("Digest processing started: %s", digest.name)

            filter_entries(feeds, digest)
            generate_digest(feeds, digest)
            digest.status = True
            digest.log += f"{timezone.now()} Digest Completed <br>"
            feed.log += f"{timezone.now()} Summary Completed <br>"
        except Exception as e:
            logging.error(
                "Task handle_digests %s: %s",
                digest.name,
                str(e),
            )
            digest.status = False
            digest.log += f"{timezone.now()} {str(e)}<br>"
        finally:
            # Explicitly clean up reference
            del feed

    # Clear the list after processing
    del feeds


def old_handle_digests(feeds: list, digest: AIFilter):
    """
    Process feeds to generate digests with memory optimizations.
    """
    
    digest.log += f"{timezone.now()} Digest processing started <br>"
    digest.status = None
    digest.save()
    feeds_count = len(feeds)
    
    # 获取过滤器和摘要生成器
    filter = digest.filter
    
    # 初始化用于存储所有接受和被过滤条目的列表
    all_discarded_entries = []
    all_accepted_entries = []
    
    # 遍历每个feed进行处理
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue

            logging.info("[Digest]Processing feed %s", feed.feed_url)
            
            # 构建包含所有条目的JSON结构，最小化token使用
            entries_data = []
            entries = feed.entries.order_by("-pubdate")[: feed.max_posts]
            
            # 为每个条目创建简洁的JSON表示
            for entry in entries:
                entry_data = {
                    "id": str(entry.id),
                    "title": entry.original_title,
                    "content": entry.ai_summary
                }
                # TODO: 如果没有ai_summary则进行summary并保存到entry里
                entries_data.append(entry_data)
            
            # 将条目数据转换为JSON字符串用于过滤
            entries_json = json.dumps(entries_data)

            # 应用过滤器获取保留的条目ID
            try: # TODO：根据max tokens进行分块
                logging.info("[Digest]Applying filter for feed %s", feed.feed_url)
                filter_result = _auto_retry(
                    func=filter.filter,
                    max_retries=3,
                    text=entries_json,
                    prompt=digest.filter_prompt,
                    digest_name=digest.name,
                    max_tokens=filter.max_tokens,
                ) if filter else None

                if not filter_result or not filter_result.get('text'):
                    logging.warning(f"No filter result for feed {feed.feed_url}")
                    digest.log += f"Filter Failure for feed {feed.feed_url}<br>"
                    continue
                
                # 解析返回的JSON数组
                retained_ids = json.loads(filter_result['text'])
                logging.info(f"Retained IDs: {retained_ids}")
                
                # 收集过滤和被过滤的entries
                for entry in entries:
                    if str(entry.id) in retained_ids:
                        all_accepted_entries.append(entry)
                    else:
                        all_discarded_entries.append(entry)
                digest.log += f"Processed feed {feed.feed_url}: {len(retained_ids)} entries retained, {len(entries) - len(retained_ids)} discarded.<br>"

            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"JSON parsing {feed.feed_url} error: {str(e)}")
                digest.log += f"Filter JSON {feed.feed_url} error: {str(e)}<br>"
            
            except Exception as e:
                logging.error(f"Filter {feed.feed_url} error: {str(e)}")
                digest.log += f"Filter {feed.feed_url} error: {str(e)}<br>"
            
            # 显式清理
            del entries_data
            del entries_json
            del entries

        except Exception as e:
            logging.error(f"Feed processing error ({feed.feed_url}): {str(e)}")
            digest.log += f"{timezone.now()} {str(e)}<br>"
    
    # 更新摘要日志和统计信息
    stats = f"Total feeds processed: {feeds_count}, Accepted entries: {len(all_accepted_entries)}, Discarded entries: {len(all_discarded_entries)}"
    
    digest.log += f"{timezone.now()} Processing completed. {stats}<br>"
    
    # 保存最终状态
    digest.save()
    
    # 清理引用
    del feeds
    del all_accepted_entries
    del all_discarded_entries

def translate_feed(feed: Feed, target_field: str = "title"):
    """Translate and summarize feed entries with memory optimizations."""
    logging.info(
        "Translating feed: %s", feed.target_language
    )
    total_tokens = 0
    total_characters = 0
    entries_to_save = []
    BATCH_SIZE = 30  # Reduced batch size for memory efficiency

    # 只处理前 feed.max_posts 条 entries
    entries = feed.entries.order_by("-pubdate")[: feed.max_posts].iterator(chunk_size=50)
    
    for entry in entries:
        try:
            logging.debug(f"Processing entry {entry}")
            if not feed.translator:
                raise Exception("Translate Engine Not Set")

            entry_needs_save = False

            # Process title translation
            if target_field == "title" and feed.translate_title:
                metrics = _translate_title(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translator,
                )
                total_tokens += metrics["tokens"]
                total_characters += metrics["characters"]
                entry_needs_save = True

            # Process content translation
            if (
                target_field == "content"
                and feed.translate_content
                and entry.original_content
            ):
                if feed.fetch_article:
                    article_content = _fetch_article_content(entry.link)
                    if article_content:
                        entry.original_content = article_content
                        entry_needs_save = True
                        # Clean up article content after use
                        del article_content

                metrics = _translate_content(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translator,
                    quality=feed.quality,
                )
                total_tokens += metrics["tokens"]
                total_characters += metrics["characters"]
                entry_needs_save = True

            if entry_needs_save:
                entries_to_save.append(entry)

            # Batch update with smaller size
            if len(entries_to_save) >= BATCH_SIZE:
                Entry.objects.bulk_update(
                    entries_to_save,
                    fields=["translated_title", "translated_content", "original_content"],
                )
                entries_to_save = []
                # Force garbage collection
                import gc
                gc.collect()

        except Exception as e:
            logging.error(f"Error processing entry {entry.link}: {str(e)}")
            feed.log += (
                f"{timezone.now()} Error processing entry {entry.link}: {str(e)}<br>"
            )
        finally:
            # Explicitly clean up entry reference
            del entry

    # Save remaining entries
    if entries_to_save:
        Entry.objects.bulk_update(
            entries_to_save,
            fields=["translated_title", "translated_content", "original_content"],
        )
        del entries_to_save

    # Update feed stats
    feed.total_tokens += total_tokens
    feed.total_characters += total_characters

    logging.info(
        f"Translation completed. Tokens: {total_tokens}, Chars: {total_characters}"
    )
    # Clean up large variables
    del entries, total_tokens, total_characters


def _translate_title(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
) -> dict:
    """Translate entry title with memory optimization."""
    total_tokens = 0
    total_characters = 0
    
    # Check if title needs translation
    if entry.translated_title:
        return {"tokens": 0, "characters": 0}

    logging.debug("[Title] Translating title")
    result = _auto_retry(
        engine.translate,
        max_retries=3,
        text=entry.original_title,
        target_language=target_language,
        text_type="title",
    )
    
    if result:
        translated_title = result.get("text")
        entry.translated_title = (
            translated_title if translated_title else entry.original_title
        )
        total_tokens = result.get("tokens", 0)
        total_characters = result.get("characters", 0)
        
    return {"tokens": total_tokens, "characters": total_characters}


def _translate_content(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    quality: bool = False,
) -> dict:
    """Translate entry content with memory optimization."""
    total_tokens = 0
    total_characters = 0
    
    # Check if content needs translation
    if entry.translated_content:
        return {"tokens": 0, "characters": 0}

    # Parse HTML with explicit cleanup
    soup = BeautifulSoup(entry.original_content, "lxml")
    
    # Add notranslate class to elements that shouldn't be translated
    for element in soup.find_all(string=True):
        if not element.get_text(strip=True):
            continue
        if text_handler.should_skip(element):
            parent = element.parent
            parent.attrs.update(
                {"class": parent.get("class", []) + ["notranslate"], "translate": "no"}
            )

    processed_html = str(soup)
    
    # Explicitly clean up BeautifulSoup object
    del soup
    import gc
    gc.collect()

    # Perform translation
    result = _auto_retry(
        func=engine.translate,
        max_retries=3,
        text=processed_html,
        target_language=target_language,
        text_type="content",
    )
    
    translated_content = result.get("text")
    entry.translated_content = (
        translated_content if translated_content else processed_html
    )
    total_tokens = result.get("tokens", 0)
    total_characters = result.get("characters", 0)
    
    # Clean up large strings
    del processed_html
    if translated_content:
        del translated_content

    return {"tokens": total_tokens, "characters": total_characters}


def summarize_feed(
    feed: Feed,
    min_chunk_size: int = 300,
    max_chunk_size: int = 1500,
    summarize_recursively: bool = True,
    max_context_chunks: int = 4,
    max_context_tokens: int = 3000,
    chunk_delimiter: str = ".",
    max_chunks_per_entry: int = 20
):
    """
    Generate content summary with memory optimizations.
    """
    assert 0 <= feed.summary_detail <= 1, "summary_detail must be between 0 and 1"
    entries_to_save = []
    total_tokens = 0
    BATCH_SIZE = 5  # Reduced batch size for memory efficiency

    try:
        # 只处理前 feed.max_posts 条 entries
        entries = (
            feed.entries
            .select_related('feed')
            .filter(ai_summary__isnull=True)
            .order_by('-pubdate')[: feed.max_posts]
            .iterator(chunk_size=30)
        )
        total_entries = (
            feed.entries
            .filter(ai_summary__isnull=True)
            .order_by('-pubdate')[: feed.max_posts]
            .count()
        )
        if not total_entries:
            logging.info(f"No entries to summarize for feed: {feed.feed_url}")
            return
            
        logging.info(f"Starting summary for {total_entries} entries in feed: {feed.feed_url}")
        
        for idx, entry in enumerate(entries):
            try:
                logging.info(f"[{idx+1}/{total_entries}] Processing: {entry.original_title}")
                
                # Clean and prepare content with explicit cleanup
                content_text = text_handler.clean_content(entry.original_content)
                
                # Skip empty content
                if not content_text.strip():
                    entry.ai_summary = "[No content available]"
                    entries_to_save.append(entry)
                    continue
                
                # Calculate chunking parameters
                token_count = text_handler.get_token_count(content_text)
                min_chunks = 1
                max_chunks = max(1, min(max_chunks_per_entry, token_count // min_chunk_size))
                target_chunks = max(1, min(max_chunks, int(
                    min_chunks + feed.summary_detail * (max_chunks - min_chunks)
                )))
                
                # Generate chunks with cleanup
                text_chunks = text_handler.adaptive_chunking(
                    content_text,
                    target_chunks=target_chunks,
                    min_chunk_size=min_chunk_size,
                    max_chunk_size=max_chunk_size,
                    initial_delimiter=chunk_delimiter
                )
                
                # Clean up original content after chunking
                del content_text
                
                actual_chunks = len(text_chunks)
                logging.info(f"Chunked into {actual_chunks} chunks (target: {target_chunks})")
                
                # Handle small content directly
                if actual_chunks == 1:
                    response = _auto_retry(
                        feed.summarizer.summarize,
                        max_retries=3,
                        text=text_chunks[0],
                        target_language=feed.target_language,
                    )
                    entry.ai_summary = response.get("text", "")
                    total_tokens += response.get("tokens", 0)
                    entries_to_save.append(entry)
                    
                    # Clean up chunks
                    del text_chunks
                    continue
                
                # Process chunks with context management
                accumulated_summaries = []
                context_token_count = 0
                
                for chunk_idx, chunk in enumerate(text_chunks):
                    # Prepare context
                    context_parts = []
                    if summarize_recursively and accumulated_summaries:
                        context_candidates = accumulated_summaries[-max_context_chunks:]
                        
                        for summary in reversed(context_candidates):
                            summary_tokens = text_handler.get_token_count(summary)
                            if context_token_count + summary_tokens <= max_context_tokens:
                                context_parts.insert(0, summary)
                                context_token_count += summary_tokens
                            else:
                                break
                    
                    # Construct prompt
                    prompt = "\n\n".join(context_parts) + "\n\nCurrent text to summarize:\n\n" + chunk if context_parts else chunk
                    
                    # Summarize with retry
                    response = _auto_retry(
                        feed.summarizer.summarize,
                        max_retries=3,
                        text=prompt,
                        target_language=feed.target_language,
                        max_tokens=max_context_tokens
                    )
                    
                    chunk_summary = response.get("text", "")
                    accumulated_summaries.append(chunk_summary)
                    total_tokens += response.get("tokens", 0)
                    context_token_count = text_handler.get_token_count(chunk_summary)
                    
                    # Clean up prompt and response
                    del prompt, response
                    
                    # Clean up chunk after processing
                    del text_chunks[chunk_idx]
                    
                # Finalize and store summary
                entry.ai_summary = "\n\n".join(accumulated_summaries)
                entries_to_save.append(entry)
                
                # Clean up accumulated summaries
                del accumulated_summaries
                
                logging.info(f"Completed summary for '{entry.original_title}' - Total tokens: {total_tokens}")
                
                # Periodically save progress with smaller batch size
                if len(entries_to_save) >= BATCH_SIZE:
                    _save_progress(entries_to_save, feed, total_tokens)
                    total_tokens = 0
                    entries_to_save = []
                    
                    # Force garbage collection
                    import gc
                    gc.collect()
                    
            except Exception as e:
                logging.error(f"Error processing entry '{entry.original_title}': {str(e)}")
                entry.ai_summary = f"[Summary failed: {str(e)}]"
                entries_to_save.append(entry)
            finally:
                # Explicitly clean up large variables
                if 'text_chunks' in locals():
                    del text_chunks
                if 'content_text' in locals():
                    del content_text
    except Exception as e:
        logging.exception(f"Critical error summarizing feed {feed.feed_url}")
        feed.log += f"{timezone.now()} Critical error: {str(e)}<br>"
    finally:
        _save_progress(entries_to_save, feed, total_tokens)
        logging.info(f"Completed summary process for feed: {feed.feed_url}")
        
        # Clean up large references
        del entries, entries_to_save



def _save_progress(entries_to_save, feed, total_tokens):
    """Save progress with memory cleanup."""
    if entries_to_save:
        Entry.objects.bulk_update(entries_to_save, fields=["ai_summary"])
        del entries_to_save
    
    if total_tokens > 0:
        feed.total_tokens += total_tokens
        feed.save()


def _auto_retry(func: callable, max_retries: int = 3, **kwargs) -> dict:
    """Retry function with exponential backoff and memory cleanup."""
    result = {}
    for attempt in range(max_retries):
        try:
            result = func(**kwargs)
            break
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(0.5 * (2**attempt))  # Exponential backoff
    
    # Clean up kwargs if they contain large objects
    for key in list(kwargs.keys()):
        if key == 'text' and isinstance(kwargs[key], str) and len(kwargs[key]) > 1000:
            del kwargs[key]
    
    return result


def _fetch_article_content(link: str) -> str:
    """Fetch full article content with explicit cleanup."""
    content = ""
    try:
        article = newspaper.Article(link)
        article.download()
        article.parse()
        content = mistune.html(article.text)
    except Exception as e:
        logging.error(f"Article fetch failed: {str(e)}")
    finally:
        # Explicitly clean up newspaper objects
        if 'article' in locals():
            del article
        return content