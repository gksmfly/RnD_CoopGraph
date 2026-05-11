import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

from ntis_client import NTISAPIError, NTISClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 파일 로드
PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("NTIS_API_KEY")
if not API_KEY:
    try:
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("NTIS_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

if not API_KEY:
    logger.error("NTIS_API_KEY not found in .env file")
    logger.error(f".env 경로: {env_path}")
    sys.exit(1)

RAW_DIR = PROJECT_ROOT / "data" / "ntis" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Output directory: {RAW_DIR}")


def safe_name(value: str) -> str:
    """파일/디렉토리명에 쓰기 편한 이름으로 변환합니다."""
    return value.replace(" ", "_").replace("/", "_")


def get_hits_count(xml_bytes: bytes) -> int:
    """원본 XML에서 현재 페이지 결과 수만 읽습니다."""
    match = re.search(rb"<HITS>\s*(\d+)\s*</HITS>", xml_bytes)
    if match:
        return int(match.group(1))

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return 0

    hits = root.findtext(".//HITS")
    if hits and hits.strip().isdigit():
        return int(hits.strip())

    return len(root.findall(".//HIT"))


def collect_data():
    """NTIS REST 원본 XML을 페이지 단위로 저장합니다."""

    client = NTISClient(API_KEY)
    saved_pages = 0
    failed_jobs = 0

    # 수집 설정: (키워드, 연도 범위)
    search_configs = [
        ("AI 반도체", 2020, 2025),
        ("온디바이스 AI", 2020, 2025),
        ("PIM", 2020, 2025),
        ("배터리", 2020, 2025),
    ]

    collections = ["project", "rpaper", "rpatent"]

    for keyword, start_year, end_year in search_configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecting data for: {keyword} ({start_year}-{end_year})")
        logger.info(f"{'='*60}")

        for collection in collections:
            try:
                target_dir = RAW_DIR / f"{collection}_{safe_name(keyword)}_{start_year}_{end_year}"
                target_dir.mkdir(parents=True, exist_ok=True)

                saved_for_job = 0
                with (target_dir / "request_urls.txt").open("w", encoding="utf-8") as url_log:
                    for page_no in range(1, 6):
                        response = client.fetch_raw(
                            collection=collection,
                            keyword=keyword,
                            page_no=page_no,
                            page_size=100,
                        )

                        page_path = target_dir / f"page_{page_no:03d}.xml"
                        page_path.parent.mkdir(parents=True, exist_ok=True)
                        page_path.write_bytes(response.content)
                        url_log.write(f"page_{page_no:03d}.xml\t{response.url}\n")

                        saved_pages += 1
                        saved_for_job += 1

                        hits_count = get_hits_count(response.content)
                        logger.info(
                            f"✓ Saved raw XML {page_path.relative_to(PROJECT_ROOT)} "
                            f"({hits_count} hits)"
                        )
                        if hits_count == 0:
                            break

                if saved_for_job == 0:
                    logger.warning(f"✗ No raw XML saved for {collection}: {keyword}")

            except NTISAPIError as e:
                failed_jobs += 1
                logger.error(f"✗ NTIS API error collecting {collection} for {keyword}: {e}")
            except Exception as e:
                failed_jobs += 1
                logger.error(f"✗ Error collecting {collection} for {keyword}: {e}")

    return saved_pages, failed_jobs


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("NTIS 데이터 수집 시작")
    logger.info("="*60)

    saved_pages, failed_jobs = collect_data()

    logger.info("\n" + "="*60)
    if saved_pages:
        logger.info("원본 XML 다운로드 완료!")
    else:
        logger.error("데이터 수집 실패: 저장된 XML이 없습니다.")
    logger.info("="*60)
    logger.info(f"저장 위치: {RAW_DIR}")
    logger.info(f"저장된 XML 페이지 수: {saved_pages}, 실패 작업 수: {failed_jobs}")
    logger.info(f"파일 목록:")
    for xml_file in sorted(RAW_DIR.glob("*/*.xml")):
        size = xml_file.stat().st_size / 1024
        logger.info(f"  - {xml_file.relative_to(RAW_DIR)} ({size:.1f} KB)")

    if not saved_pages:
        sys.exit(2)
