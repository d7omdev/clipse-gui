from datetime import datetime, timedelta


def format_date(date_str):
    """Formats an ISO date string into a user-friendly relative format."""
    if not date_str:
        return "Unknown date"
    try:
        # Parse ISO string, handling potential timezone info
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Get current time, making it offset-aware using the parsed dt's timezone
        # Or using local timezone if dt is naive (though ISO usually implies offset)
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)
        else:
            # Fallback: Assume naive dt refers to local time
            # This might be inaccurate if the source timestamp was UTC but lacks 'Z' or offset
            now = datetime.now()
            # Or assume UTC if naive:
            # dt = dt.replace(tzinfo=timezone.utc)
            # now = datetime.now(timezone.utc)

        today = now.date()
        yesterday = today - timedelta(days=1)
        dt_date = dt.date()  # Compare dates only

        if dt_date == today:
            return f"Today at {dt.strftime('%H:%M')}"
        elif dt_date == yesterday:
            return f"Yesterday at {dt.strftime('%H:%M')}"
        elif dt.year == now.year:
            return dt.strftime("%b %d, %H:%M")  # e.g., Aug 15, 14:30
        else:
            return dt.strftime("%b %d, %Y, %H:%M")  # e.g., Aug 15, 2023, 14:30
    except Exception as e:
        print(f"Date formatting error for '{date_str}': {e}")
        return date_str  # Return original string if format fails


def fuzzy_search(
    items,
    search_term,
    value_key="value",
    path_key="filePath",
    pinned_key="pinned",
    show_only_pinned=False,
):
    """
    Performs a fuzzy search on a list of dictionary items.

    Args:
        items (list): List of dictionaries containing items to search
        search_term (str): The search query string
        value_key (str): Dictionary key for the primary text to search within items
        path_key (str): Dictionary key for secondary text to search (like file paths)
        pinned_key (str): Dictionary key for pinned status
        show_only_pinned (bool): Whether to show only pinned items

    Returns:
        list: Filtered items as dicts with format {"original_index": index, "item": item, "match_quality": score}
    """
    filtered_items = []
    search_term_lower = search_term.lower() if search_term else ""

    if not search_term_lower or (show_only_pinned and not search_term_lower):
        for index, item in enumerate(items):
            is_pinned = item.get(pinned_key, False)
            if show_only_pinned and not is_pinned:
                continue
            filtered_items.append({"original_index": index, "item": item})
    else:
        search_tokens = search_term_lower.split()

        for index, item in enumerate(items):
            is_pinned = item.get(pinned_key, False)
            if show_only_pinned and not is_pinned:
                continue

            item_value = item.get(value_key, "").lower()
            file_path = item.get(path_key, "").lower()

            # Simple token matching
            all_tokens_match = True
            match_quality = 0

            for token in search_tokens:
                # Perfect match gets highest score
                if token in item_value or token in file_path:
                    match_quality += 100
                    continue

                # Check for partial matches (beginning of words)
                words_in_value = item_value.split()
                words_in_path = file_path.split() if file_path else []

                partial_match = False
                for word in words_in_value + words_in_path:
                    if word.startswith(token):
                        match_quality += 75
                        partial_match = True
                        break
                    elif token.startswith(word) and len(word) >= 3:
                        match_quality += 60
                        partial_match = True
                        break

                # Check for close matches (levenshtein-like approach)
                if not partial_match:
                    # Simple character-level similarity
                    best_similarity = 0
                    for word in words_in_value + words_in_path:
                        if len(word) > 2:  # Only consider meaningful words
                            # Calculate similarity by checking character overlap
                            similarity = _calculate_similarity(word, token)
                            best_similarity = max(best_similarity, similarity)

                    if best_similarity > 0.7:  # 70% similarity threshold
                        match_quality += int(best_similarity * 50)
                        partial_match = True

                # If this token doesn't match at all, item doesn't match search
                if not partial_match:
                    all_tokens_match = False
                    break

            if all_tokens_match and match_quality > 0:
                filtered_items.append(
                    {
                        "original_index": index,
                        "item": item,
                        "match_quality": match_quality,
                    }
                )

        # Sort results by match quality
        filtered_items.sort(key=lambda x: x.get("match_quality", 0), reverse=True)

    return filtered_items


def _calculate_similarity(str1, str2):
    """Calculate a simple character-based similarity between two strings."""
    set1, set2 = set(str1), set(str2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    if not union:
        return 0.0
    basic_score = len(intersection) / len(union)
    len_ratio = (
        min(len(str1), len(str2)) / max(len(str1), len(str2))
        if max(len(str1), len(str2)) > 0
        else 0
    )
    return (basic_score * 0.7) + (len_ratio * 0.3)
