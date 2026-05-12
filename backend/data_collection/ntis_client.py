# backend/data_collection/ntis_client.py
# NTIS Open API 클라이언트
# 기능: XML 응답을 파싱하여 DataFrame으로 변환 / 3개 컬렉션(과제,논문,특허) 지원

import logging
import warnings
import xml.etree.ElementTree as ET
from typing import Dict, Optional

import pandas as pd
import requests
from urllib3.exceptions import InsecureRequestWarning

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class NTISAPIError(RuntimeError):
    """NTIS API가 정상 XML 결과를 반환하지 않을 때 발생합니다."""


class NTISClient:
    """NTIS Open API 클라이언트"""

    TOTAL_SEARCH_URL = "https://www.ntis.go.kr/rndopen/openApi/totalRstSearch"

    COLLECTIONS = {
        "project": TOTAL_SEARCH_URL,
        "rpaper": TOTAL_SEARCH_URL,
        "rpatent": TOTAL_SEARCH_URL,
    }

    def __init__(self, api_key: str):
        self.api_key = api_key

    def build_params(
        self,
        collection: str,
        keyword: str,
        page_no: int = 1,
        page_size: int = 100,
    ) -> Dict:
        """NTIS 기관용 통합검색 요청 파라미터를 생성합니다."""
        if collection not in self.COLLECTIONS:
            raise ValueError(f"collection must be one of {list(self.COLLECTIONS.keys())}")

        start_position = ((page_no - 1) * page_size) + 1

        return {
            "apprvKey": self.api_key,
            "query": keyword,
            "userId": "",
            "collection": collection,
            "searchField": "",
            "startPosition": start_position,
            "displayCount": page_size,
            "naviCount": 10,
            "sortby": "",
            "boostquery": "",
            "addQuery": "",
        }

    def fetch_raw(
        self,
        collection: str,
        keyword: str,
        page_no: int = 1,
        page_size: int = 100,
    ) -> requests.Response:
        """NTIS REST 응답을 변환하지 않고 원본 Response로 반환합니다."""
        if collection not in self.COLLECTIONS:
            raise ValueError(f"collection must be one of {list(self.COLLECTIONS.keys())}")

        start_position = ((page_no - 1) * page_size) + 1
        logger.info(
            f"Fetching raw {collection}: {keyword} "
            f"- Page {page_no}, startPosition={start_position}"
        )

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Charset": "utf-8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "identity",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        }
        response = requests.get(
            self.COLLECTIONS[collection],
            params=self.build_params(collection, keyword, page_no, page_size),
            headers=headers,
            timeout=20,
            allow_redirects=True,
            verify=False,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        self._validate_response(response)
        return response

    def search(
        self,
        collection: str,
        keyword: str,
        start_year: int,
        end_year: int,
        page_no: int = 1,
        page_size: int = 100
    ) -> pd.DataFrame:
        """
        NTIS API 검색

        Args:
            collection: "project", "rpaper", "rpatent"
            keyword: 검색 키워드
            start_year: 시작 연도
            end_year: 종료 연도
            page_no: 페이지 번호 (1부터 시작)
            page_size: 페이지당 결과 수 (최대 100)

        Returns:
            DataFrame 형식의 검색 결과
        """
        try:
            response = self.fetch_raw(collection, keyword, page_no, page_size)
            df = self._parse_xml(response.text, collection)
            df = self._filter_years(df, collection, start_year, end_year)
            logger.info(f"Retrieved {len(df)} records")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def search_all_pages(
        self,
        collection: str,
        keyword: str,
        start_year: int,
        end_year: int,
        page_size: int = 100,
        max_pages: Optional[int] = None
    ) -> pd.DataFrame:
        """
        모든 페이지 자동 수집

        Args:
            max_pages: 최대 페이지 수 (None이면 모든 페이지 수집)
        """
        all_results = []
        page_no = 1

        while True:
            if max_pages and page_no > max_pages:
                break

            df = self.search(collection, keyword, start_year, end_year, page_no, page_size)

            if df.empty:
                if max_pages:
                    page_no += 1
                    continue
                break

            all_results.append(df)
            page_no += 1

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        else:
            return pd.DataFrame()

    def _parse_xml(self, xml_text: str, collection: str) -> pd.DataFrame:
        """XML 응답을 DataFrame으로 변환"""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            snippet = xml_text[:200].replace("\n", " ")
            raise NTISAPIError(f"XML parsing error: {e}; response starts with: {snippet}") from e

        if root.tag.lower() == "error":
            raise NTISAPIError(
                "NTIS API returned an error. NTIS_API_KEY가 국가R&D 통합검색 "
                "서비스(기관용)에 승인된 키인지 확인하세요."
            )

        records = []
        hits = root.findall(".//HIT")

        if collection == "project":
            for item in hits:
                record = self._extract_project(item)
                records.append(record)
        elif collection == "rpaper":
            for item in hits:
                record = self._extract_paper(item)
                records.append(record)
        elif collection == "rpatent":
            for item in hits:
                record = self._extract_patent(item)
                records.append(record)

        return pd.DataFrame(records)

    def _validate_response(self, response: requests.Response) -> None:
        """차단/리다이렉트/HTML 응답을 빈 결과로 오인하지 않게 검증합니다."""
        location = response.headers.get("Location", "")
        content_type = response.headers.get("Content-Type", "")
        text_head = response.text[:500].lower()

        if "access_check" in response.url.lower():
            raise NTISAPIError(
                f"NTIS request was redirected to a blocked page: {response.url}"
            )

        if "html" in content_type.lower() or "<html" in text_head or "blocked page" in text_head:
            raise NTISAPIError(
                "NTIS returned an HTML block/error page instead of XML. "
                "Check the endpoint, approval key, and access permissions."
            )

    def _extract_project(self, item: ET.Element) -> Dict:
        """과제 정보 추출"""
        return {
            "ProjectID": self._get_text(item, "ProjectNumber"),
            "ProjectName": self._get_text(item, "ProjectTitle"),
            "Organization": self._get_text(item, "ResearchAgency"),
            "PrincipalInvestigator": self._get_text(item, "Manager"),
            "StartYear": self._get_text(item, "ProjectYear"),
            "EndYear": self._get_text(item, "ProjectYear"),
            "ProjectPeriodStart": self._get_text(item, "TotalStart"),
            "ProjectPeriodEnd": self._get_text(item, "TotalEnd"),
            "Budget": self._get_text(item, "TotalFunds"),
            "GovernmentFunds": self._get_text(item, "GovernmentFunds"),
            "TechnologyClassification": self._get_text(item, "ScienceClass"),
            "Division": self._get_text(item, "Ministry"),
            "Abstract": self._get_text(item, "Abstract"),
            "Goal": self._get_text(item, "Goal"),
            "Keywords": self._get_text(item, "Keyword"),
        }

    def _extract_paper(self, item: ET.Element) -> Dict:
        """논문 정보 추출"""
        return {
            "ProjectID": self._get_text(item, "ProjectID"),
            "PaperTitle": self._get_text(item, "ResultTitle"),
            "Authors": self._get_text(item, "Author"),
            "PublicationYear": self._get_text(item, "PubYear"),
            "JournalName": self._get_text(item, "JournalName"),
            "Abstract": self._get_text(item, "Abstract"),
            "DOI": self._get_text(item, "DigitalObjectIdentifier"),
            "ProjectTitle": self._get_text(item, "ProjectTitle"),
        }

    def _extract_patent(self, item: ET.Element) -> Dict:
        """특허 정보 추출"""
        return {
            "ProjectID": self._get_text(item, "ProjectID"),
            "PatentTitle": self._get_text(item, "ResultTitle"),
            "PatentNumber": self._get_text(item, "RegistNumber"),
            "FilingDate": None,
            "RegistrationDate": self._get_text(item, "Year"),
            "Inventor": self._get_text(item, "Registrant"),
            "Abstract": self._get_text(item, "Abstract"),
            "ProjectTitle": self._get_text(item, "ProjectTitle"),
            "RegistrationCountry": self._get_text(item, "RegistCountry"),
            "RegistrationType": self._get_text(item, "RegistType"),
        }

    def _filter_years(
        self,
        df: pd.DataFrame,
        collection: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame:
        """NTIS 공개 API는 연도 파라미터가 없어 응답 후 연도를 필터링합니다."""
        if df.empty:
            return df

        year_column = {
            "project": "StartYear",
            "rpaper": "PublicationYear",
            "rpatent": "RegistrationDate",
        }[collection]

        years = pd.to_numeric(df[year_column], errors="coerce")
        return df[(years >= start_year) & (years <= end_year)].reset_index(drop=True)

    @staticmethod
    def _get_text(element: ET.Element, tag: str) -> Optional[str]:
        """XML 요소에서 텍스트 추출"""
        sub = element.find(tag)
        if sub is None:
            return None
        text = "".join(sub.itertext()).strip()
        return text or None
