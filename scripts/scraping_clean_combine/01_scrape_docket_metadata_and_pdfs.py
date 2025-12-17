import json
import csv
import urllib.parse
import urllib.request
import re
import html
import os
import time
from urllib.error import HTTPError, URLError
from io import BytesIO
from PyPDF2.errors import DependencyError
from PyPDF2 import PdfReader

# python -m pip install PyPDF2
# python -m pip install pycryptodome
# python -m pip install pandas

# ==== !! Change API Key, Output, Docket ID ====
    # API_KEY = ""
    # OUTPUT_DIR = ""
    # docket_id = ""
# ---- Adjustable parameters -----
# ! API limit: 900/hr
# Adjust based on the docket comment count
    # page_size = 
    # CHUNK_START_PAGE = 
    # CHUNK_END_PAGE   = 
# Pre-processing function, adjust per your needs
    # clean_comment_html
# ==============================================

# Output: JSON + CSV with comment text (HTML cleaned) + PDF extracted text

# -------------------- Configurations -------------------- #
API_KEY = ""  # !!! <<< API key
BASE_URL = "https://api.regulations.gov/v4"


# -------------------- Base http tool -------------------- #
def get_json(url, params=None, max_retries=5):
    attempt = 0
    while True:
        if params:
            query_str = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_str}"
        else:
            full_url = url

        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "python-urllib/regulations-scraper",
                "X-Api-Key": API_KEY,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)

        except HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = 2 ** attempt
                else:
                    delay = 2 ** attempt
                delay = min(delay, 120)
                attempt += 1
                print(f"[WARN] HTTP 429 Too Many Requests, wait {delay} seconds before retry ({attempt}/{max_retries})")
                time.sleep(delay)
                continue
            raise

def get_binary(url, max_retries=5):
    attempt = 0
    while True:
        # Add api_key to URL if missing for downloads.regulations.gov
        final_url = url
        if "downloads.regulations.gov" in url and "api_key=" not in url:
            sep = "&" if "?" in url else "?"
            final_url = f"{url}{sep}api_key={API_KEY}"

        req = urllib.request.Request(
            final_url,
            headers={
                # Mimic real browser
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                # Add API key to avoid 403 (may fail to fatch pdf is not added, 1/3 times)
                "X-Api-Key": API_KEY,
                "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = 2 ** attempt
                else:
                    delay = 2 ** attempt
                delay = min(delay, 120)
                attempt += 1
                print(f"[WARN] 429 when downloading PDF, wait {delay} seconds and reattempt ({attempt}/{max_retries})")
                time.sleep(delay)
                continue

            print(f"[WARN] fail to download PDF, HTTP {e.code}, url={final_url}")
            return b""
        except URLError as e:
            if attempt < max_retries:
                delay = 2 ** attempt
                attempt += 1
                print(f"[WARN] Internet Error {e.reason}, wait {delay} seconds and reattempt ({attempt}/{max_retries})")
                time.sleep(delay)
                continue
            print(f"[WARN] PDF download failure, url={final_url}")
            return b""


# -------------------- Pre-processing -------------------- #
def clean_comment_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 20) -> str:

    if not PdfReader:
        return ""

    if not pdf_bytes:
        return ""

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except DependencyError as e:
        # PyCryptodome not installed for AES encripted PDF
        print(f"[WARN] This PDF needs PyCryptodome to decode: {e}")
        return ""
    except Exception as e:
        print(f"[WARN] Failed to : {e}")
        return ""

    texts = []
    try:
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            texts.append(page_text)
    except DependencyError as e:
        print(f"[WARN] Enconter decoding issue, skipped: {e}")
        return ""
    except Exception as e:
        print(f"[WARN] Enconter page issue, skipped: {e}")
        return ""

    text = "\n\n".join(texts)
    text = re.sub(r"\s+", " ", text).strip()
    return text



# -------------------- API Packaging -------------------- #
def get_comment_detail_by_id(comment_id: str) -> dict:

    url = f"{BASE_URL}/comments/{comment_id}"
    params = {"api_key": API_KEY, "include": "attachments"}
    data = get_json(url, params)
    return data

def _collect_from_file_formats(file_formats):
    urls = []
    if isinstance(file_formats, list):
        for ff in file_formats:
            if not isinstance(ff, dict):
                continue
            url = ff.get("fileUrl") or ff.get("url")
            if not url:
                continue
            file_type = (ff.get("fileType") or ff.get("contentType") or "").lower()
            if "pdf" in file_type or url.lower().endswith(".pdf") or "contentType=pdf" in url.lower():
                urls.append(url)
    return urls


def _scan_for_pdf_urls(obj):

    pdf_urls = []
    if isinstance(obj, dict):
        # Handle fileFormats key
        if "fileFormats" in obj:
            pdf_urls.extend(_collect_from_file_formats(obj["fileFormats"]))
        # Recurse into values
        for v in obj.values():
            pdf_urls.extend(_scan_for_pdf_urls(v))
    elif isinstance(obj, list):
        for item in obj:
            pdf_urls.extend(_scan_for_pdf_urls(item))
    return pdf_urls


def get_pdf_urls_from_detail(detail: dict) -> list:

    pdf_urls = []

    data = detail.get("data") or {}
    attrs = data.get("attributes") or {}

    # 1) attachments / fileFormats under attributes
    pdf_urls.extend(_scan_for_pdf_urls(attrs.get("attachments")))
    pdf_urls.extend(_scan_for_pdf_urls(attrs.get("fileFormats")))

    # 2) included[*].attributes.fileFormats / attachments
    for inc in detail.get("included") or []:
        inc_attrs = inc.get("attributes") or {}
        pdf_urls.extend(_scan_for_pdf_urls(inc_attrs))

    # de-duplicate
    deduped = list(dict.fromkeys(pdf_urls))
    return deduped

# ----------- Main logic: fetch comment by page + process HTML + PDF ------------ #
def get_comments_with_text_and_pdfs(
    docket_id: str,
    page_size: int = 250,
    start_page: int = 1,
    end_page: int | None = None,
    per_detail_sleep: float = 0.3,
):
    url = f"{BASE_URL}/comments"

    all_results = []
    page_number = start_page
    total_from_meta = None

    while True:
        params = {
            "filter[docketId]": docket_id,
            "page[size]": str(page_size),
            "page[number]": str(page_number),
            "api_key": API_KEY,
        }

        print(
            f"=== Require page {page_number} comments"
            f"(docketId={docket_id}, page[size]={page_size}) ==="
        )
        data = get_json(url, params)

        meta = data.get("meta", {}) or {}
        items = data.get("data", []) or []
        total_from_meta = meta.get("totalElements")
        total_pages = meta.get("totalPages")
        has_next = meta.get("hasNextPage")

        print(
            f"  Fetched {len(items)} items；"
            f" meta.totalElements={total_from_meta}, meta.totalPages={total_pages}, meta.hasNextPage={has_next}"
        )

        if not items:
            print(" No more data on this page, stop.")
            break

        for idx, item in enumerate(items, start=1):
            base_attrs = item.get("attributes", {}) or {}
            comment_id = item.get("id")

            # ---- Get HTML comment ----
            raw_comment_html = (
                base_attrs.get("comment")
                or base_attrs.get("commentText")
                or ""
            )
            clean_html_text = clean_comment_html(raw_comment_html)

            # ---- Get detail：Garantee attachments + more complete text ----
            detail = None
            detail_attrs = {}
            try:
                detail = get_comment_detail_by_id(comment_id)
                detail_attrs = (detail.get("data") or {}).get("attributes", {}) or {}
                # If no comment in list, try detail
                if not raw_comment_html:
                    raw_comment_html = (
                        detail_attrs.get("comment")
                        or detail_attrs.get("commentText")
                        or ""
                    )
                    clean_html_text = clean_comment_html(raw_comment_html)
            except HTTPError as e:
                print(f"[WARN] Fail to extract commentId={comment_id}, HTTP {e.code}, jump over detail.")
            except URLError as e:
                print(f"[WARN] Network error for getting details commentId={comment_id}, reason: {e.reason}, jump over detail.")

            time.sleep(per_detail_sleep)

            # ---- KEYWORD：if attach shows up (see attached file(s), attached request) ----
            search_str = " ".join(
                [
                    base_attrs.get("title") or "",
                    detail_attrs.get("title") or "",
                    clean_html_text or "",
                ]
            )
            has_attach_keyword = bool(re.search(r"attach", search_str, flags=re.I))

            # ---- If there's attachment in detail download PDF ----
            pdf_urls = []
            pdf_text = ""
            if detail:
                pdf_urls = get_pdf_urls_from_detail(detail)

                if pdf_urls:
                    print(f"  commentId={comment_id} find {len(pdf_urls)} attachments, start extract PDF text...")
                    all_pdf_texts = []
                    for u in pdf_urls:
                        pdf_bytes = get_binary(u)
                        text_one = extract_text_from_pdf_bytes(pdf_bytes, max_pages=20)
                        if text_one:
                            all_pdf_texts.append(text_one)
                        time.sleep(0.1)  # sleep between PDF downloads

                    if all_pdf_texts:
                        pdf_text = "\n\n----- [PDF_SEP] -----\n\n".join(all_pdf_texts)
                        pdf_text = re.sub(r"\s+", " ", pdf_text).strip()

            # ---- Merge HTML and PDF text ----
            combined_parts = []
            if clean_html_text:
                combined_parts.append(clean_html_text)
            if pdf_text:
                combined_parts.append("[PDF_TEXT]\n" + pdf_text)

            combined_text = "\n\n".join(combined_parts).strip()

            # Ignore if no text at all
            if not combined_text:
                continue

            attrs = detail_attrs or base_attrs

            row = {
                "commentId": comment_id,
                "agencyId": attrs.get("agencyId") or base_attrs.get("agencyId"),
                "docketId": attrs.get("docketId") or base_attrs.get("docketId"),
                "documentId": attrs.get("documentId") or base_attrs.get("documentId"),
                "commentOnId": attrs.get("commentOnId") or base_attrs.get("commentOnId"),
                "documentType": attrs.get("documentType") or base_attrs.get("documentType"),
                "postedDate": attrs.get("postedDate") or base_attrs.get("postedDate"),
                "receiveDate": attrs.get("receiveDate") or base_attrs.get("receiveDate"),
                "title": attrs.get("title") or base_attrs.get("title"),
                "trackingNbr": attrs.get("trackingNbr") or base_attrs.get("trackingNbr"),
                "organizationName": attrs.get("organization") or base_attrs.get("organization"),
                "firstName": attrs.get("firstName") or base_attrs.get("firstName"),
                "lastName": attrs.get("lastName") or base_attrs.get("lastName"),
                "city": attrs.get("city") or base_attrs.get("city"),
                "stateProvinceRegion": attrs.get("stateProvinceRegion") or base_attrs.get("stateProvinceRegion"),
                "country": attrs.get("country") or base_attrs.get("country"),
                "withdrawn": attrs.get("withdrawn") or base_attrs.get("withdrawn"),
                "restrictReasonType": attrs.get("restrictReasonType") or base_attrs.get("restrictReasonType"),
                "restrictReason": attrs.get("restrictReason") or base_attrs.get("restrictReason"),
                "rawCommentHtml": raw_comment_html,
                "cleanCommentHtml": clean_html_text,
                "pdfText": pdf_text,
                "combinedText": combined_text,
                "pdfUrls": ";".join(pdf_urls),
                "hasSeeAttachedHint": has_attach_keyword,
            }

            all_results.append(row)

            if page_number == start_page and idx <= 3:
                print("  Sample combinedText(preview): ", combined_text[:200], "...\n")

        if has_next is False:
            print("  meta.hasNextPage = False, stop.")
            break

        if end_page is not None and page_number >= end_page:
            print(f" Reach set end_page={end_page}, stop.")
            break

        page_number += 1
        time.sleep(0.5)

    print(
        f"\n==== API have {total_from_meta} records: "
        f"Between {start_page}-{end_page or page_number} pages, "
        f"Fetched {len(all_results)} records with HTML + PDF ====\n"
    )

    return all_results


# -------------------- main：set up docket + make page into blocks -------------------- #
if __name__ == "__main__":
    #==== Change Output Directory =====
    OUTPUT_DIR = "" # <<< !!! Change your Output Directory here !!!
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    #==== Change Docket ID =====
    docket_id = "" # <<< !!! Change your docket ID here !!!
    page_size = 250

    #==== Page Section =====
    CHUNK_START_PAGE = 1
    CHUNK_END_PAGE   = 2

    comments_with_text = get_comments_with_text_and_pdfs(
        docket_id,
        page_size=page_size,
        start_page=CHUNK_START_PAGE,
        end_page=CHUNK_END_PAGE,
        per_detail_sleep=0.3,
    )

    print(f"==== Fetched {len(comments_with_text)} records, combinedText is not empty ====\n")

    # ===== Export JSON =====
    json_filename = os.path.join(
        OUTPUT_DIR,
        f"{docket_id}_comments_text_pdf_p{CHUNK_START_PAGE}_to_p{CHUNK_END_PAGE}.json"
    )
    with open(json_filename, "w", encoding="utf-8") as f_json:
        json.dump(comments_with_text, f_json, ensure_ascii=False, indent=2)
    print("JSON saved to:", json_filename)

    # ===== Export CSV =====
    csv_filename = os.path.join(
        OUTPUT_DIR,
        f"{docket_id}_comments_text_pdf_p{CHUNK_START_PAGE}_to_p{CHUNK_END_PAGE}.csv"
    )
    fieldnames = [
        "commentId",
        "agencyId",
        "docketId",
        "documentId",
        "commentOnId",
        "documentType",
        "postedDate",
        "receiveDate",
        "title",
        "trackingNbr",
        "organizationName",
        "firstName",
        "lastName",
        "city",
        "stateProvinceRegion",
        "country",
        "withdrawn",
        "restrictReasonType",
        "restrictReason",
        "rawCommentHtml",
        "cleanCommentHtml",
        "pdfText",
        "combinedText",
        "pdfUrls",
        "hasSeeAttachedHint",
    ]

    with open(csv_filename, "w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()
        for row in comments_with_text:
            writer.writerow(row)
    print("CSV saved to:", csv_filename)

    print("\nCurrent Path:", os.getcwd())
