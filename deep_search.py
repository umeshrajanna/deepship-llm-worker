"""
Enhanced HTML App Generator with Multi-Stage Research Pipeline + Web Scraping

This generator matches Perplexity's quality by:
1. Planning research before building
2. Executing multiple targeted searches
3. Scraping and extracting structured data from URLs using NoirScraper
4. Extracting structured data from results
5. Generating with comprehensive context
"""

import json
import re
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union, Tuple, Callable
# from openai import AsyncOpenAI
import aiohttp
from pathlib import Path

# Import the enhanced transformer
from query_transformer import EnhancedQueryTransformer

from anthropic import Anthropic
import os

from dotenv import load_dotenv
load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Google Custom Search API credentials
GOOGLE_API_KEY = "AIzaSyDGUJz3wavssYikx5wDq0AcD2QlRt4vS5c"
GOOGLE_CSE_ID = "650310331e0e3490e"

# NoirScraper API endpoint
NOIR_SCRAPER_URL = "https://noirscraper-production.up.railway.app/scrape_and_extract"


class WebScraper:
    """Web scraper using NoirScraper API"""
    
class WebScraper:
    """Web scraper using NoirScraper API"""
    
    @staticmethod
    def scrape_urls(
        urls: List[str],
        query: str,
        timeout: int = 30,
        chunk_size: int = 400,
        concurrency: int = 10
    ) -> List[Dict]:
        """
        Scrape multiple URLs using NoirScraper API (SYNCHRONOUS)
        
        Args:
            urls: List of URLs to scrape
            query: Search query for relevance scoring
            timeout: Request timeout in seconds
            chunk_size: Size of text chunks for processing (default: 400)
            concurrency: Number of concurrent scraping operations (default: 10)
            
        Returns:
            List of scrape results with format:
            {
                'url': str,
                'best_chunk': str,
                'score': float,
                'chunk_index': int,
                'word_count': int,
                'total_chunks': int,
                'tables': List[Dict],
                'tables_count': int,
                'error': str (optional)
            }
        """
        
        payload = {
            "urls": urls,
            "chunk_size": chunk_size,
            "query": query,
            "concurrency": concurrency
        }
        
        try:
            import requests
            
            print(f"[SCRAPER] Sending request to NoirScraper for {len(urls)} URLs...")
            
            response = requests.post(
                NOIR_SCRAPER_URL,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                print(f"[SCRAPER] Error: Status {response.status_code}")
                return [{
                    'url': url,
                    'best_chunk': '',
                    'score': 0.0,
                    'chunk_index': -1,
                    'word_count': 0,
                    'total_chunks': 0,
                    'tables': [],
                    'tables_count': 0,
                    'error': f'HTTP {response.status_code}'
                } for url in urls]
            
            data = response.json()
            
            # Handle NoirScraper's response format: {"ok": true, "results": [...]}
            if isinstance(data, dict):
                # Check for success
                if not data.get('ok', False):
                    error_msg = data.get('error', 'Unknown error')
                    print(f"[SCRAPER] API returned error: {error_msg}")
                    return [{
                        'url': url,
                        'best_chunk': '',
                        'score': 0.0,
                        'chunk_index': -1,
                        'word_count': 0,
                        'total_chunks': 0,
                        'tables': [],
                        'tables_count': 0,
                        'error': error_msg
                    } for url in urls]
                
                # Extract results array
                if 'results' in data:
                    results = data['results']
                    if not isinstance(results, list):
                        print(f"[SCRAPER] Results is not a list")
                        return [{
                            'url': url,
                            'best_chunk': '',
                            'score': 0.0,
                            'chunk_index': -1,
                            'word_count': 0,
                            'total_chunks': 0,
                            'tables': [],
                            'tables_count': 0,
                            'error': 'Invalid results format'
                        } for url in urls]
                    
                    # Log statistics if available
                    if 'statistics' in data:
                        stats = data['statistics']
                        print(f"[SCRAPER] Stats: {stats.get('successful_scrapes', 0)}/{stats.get('urls_requested', 0)} URLs, "
                              f"{stats.get('total_tables_found', 0)} tables, "
                              f"avg score: {stats.get('average_relevance_score', 0):.2f}")
                    
                    if 'timing' in data:
                        timing = data['timing']
                        print(f"[SCRAPER] Timing: scrape={timing.get('scrape_seconds', 0):.1f}s, "
                              f"processing={timing.get('processing_seconds', 0):.1f}s, "
                              f"total={data.get('total_duration_seconds', 0):.1f}s")
                    
                    print(f"[SCRAPER] Successfully received {len(results)} scrape results")
                    return results
                else:
                    print(f"[SCRAPER] No 'results' field in response")
                    return [{
                        'url': url,
                        'best_chunk': '',
                        'score': 0.0,
                        'chunk_index': -1,
                        'word_count': 0,
                        'total_chunks': 0,
                        'tables': [],
                        'tables_count': 0,
                        'error': 'No results field'
                    } for url in urls]
            
            # Fallback: if response is directly an array (old format)
            elif isinstance(data, list):
                print(f"[SCRAPER] Received legacy format (array)")
                return data
            
            else:
                print(f"[SCRAPER] Unexpected response format: {type(data)}")
                return [{
                    'url': url,
                    'best_chunk': '',
                    'score': 0.0,
                    'chunk_index': -1,
                    'word_count': 0,
                    'total_chunks': 0,
                    'tables': [],
                    'tables_count': 0,
                    'error': 'Invalid response format'
                } for url in urls]
            
        except requests.exceptions.Timeout:
            print(f"[SCRAPER] Timeout after {timeout}s")
            return [{
                'url': url,
                'best_chunk': '',
                'score': 0.0,
                'chunk_index': -1,
                'word_count': 0,
                'total_chunks': 0,
                'tables': [],
                'tables_count': 0,
                'error': 'Timeout'
            } for url in urls]
        except requests.exceptions.RequestException as e:
            print(f"[SCRAPER] Request exception: {e}")
            import traceback
            traceback.print_exc()
            return [{
                'url': url,
                'best_chunk': '',
                'score': 0.0,
                'chunk_index': -1,
                'word_count': 0,
                'total_chunks': 0,
                'tables': [],
                'tables_count': 0,
                'error': f'Request failed: {str(e)}'
            } for url in urls]
        except Exception as e:
            print(f"[SCRAPER] Unexpected exception: {e}")
            import traceback
            traceback.print_exc()
            return [{
                'url': url,
                'best_chunk': '',
                'score': 0.0,
                'chunk_index': -1,
                'word_count': 0,
                'total_chunks': 0,
                'tables': [],
                'tables_count': 0,
                'error': str(e)
            } for url in urls]
            
class WebSearcher:
    """Enhanced web searcher with better result handling"""
    
   
    from typing import List, Dict

    @staticmethod
    def search_google(query: str, num_results: int = 10) -> List[Dict]:
        """
        Perform Google Custom Search (SYNC version)
        Returns: List of {title, link, snippet}
        """
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "num": min(num_results, 10)
        }
        
        try:
            import requests
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"[SEARCH] Error: Status {response.status_code}")
                return []
            
            data = response.json()
            
            results = []
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            return results
            
        except requests.exceptions.Timeout:
            print(f"[SEARCH] Request timed out")
            return []
        except Exception as e:
            print(f"[SEARCH] Exception: {e}")
            return []

class DataExtractor:
    """Extracts structured data from search results and scraped content"""
    
    @staticmethod
    def extract_structured_data(
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        data_types: List[str],
        user_query: str
    ) -> Dict:
        """
        Extract structured data from all search results and scraped content
        
        Args:
            search_results: Dict mapping queries to their results
            scraped_results: List of scraped content from NoirScraper
            data_types: Types of data to extract
            user_query: Original user query for context
            
        Returns:
            Structured data as JSON
        """
        
        # Format search results
        results_context = ""
        for query, results in search_results.items():
            results_context += f"\n\n=== Search: {query} ===\n"
            for i, result in enumerate(results, 1):
                results_context += f"\n{i}. {result['title']}\n"
                results_context += f"   {result['snippet']}\n"
        
        # Format scraped content
        scraped_context = ""
        if scraped_results:
            scraped_context = "\n\n=== SCRAPED CONTENT ===\n"
            
            for i, scrape in enumerate(scraped_results, 1):
                if scrape.get('error'):
                    continue
                    
                scraped_context += f"\n--- Source {i}: {scrape['url']} ---\n"
                scraped_context += f"Relevance Score: {scrape['score']:.2f}\n"
                
                # Add best chunk
                if scrape.get('best_chunk'):
                    scraped_context += f"\nContent (chunk {scrape['chunk_index']}/{scrape['total_chunks']}):\n"
                    scraped_context += scrape['best_chunk'][:2000]  # Limit length
                    scraped_context += "\n"
                
                # Add tables
                if scrape.get('tables'):
                    scraped_context += f"\nTables Found: {scrape['tables_count']}\n"
                    for j, table in enumerate(scrape['tables'], 1):
                        scraped_context += f"\nTable {j}:\n"
                        scraped_context += json.dumps(table, indent=2)[:1000]  # Limit length
                        scraped_context += "\n"
        
        extraction_prompt = f"""Extract structured data from these search results and scraped web pages.

USER REQUEST: {user_query}
DATA TYPES NEEDED: {', '.join(data_types)}

SEARCH RESULTS:
{results_context}
{scraped_context}

TASK: Extract and structure the data found in these results.

RULES:
1. Extract SPECIFIC VALUES: numbers, percentages, dates, names
2. Create a well-structured JSON object
3. Include source attribution (URL) where possible
4. Parse dates into standard format (YYYY-MM-DD)
5. Convert text descriptions to actual values
6. Organize data logically by category/entity
7. PRIORITIZE data from scraped content (best_chunk and tables) as it's more complete
8. Extract tabular data into structured arrays/objects
9. Preserve numerical precision from tables

EXAMPLES OF GOOD EXTRACTION:

For economic data:
{{
  "countries": {{
    "United States": {{
      "gdp_growth": 1.8,
      "inflation": 3.2,
      "unemployment": 4.2,
      "interest_rate": 4.38,
      "source": "https://example.com/data",
      "last_updated": "2025-05"
    }}
  }}
}}

For tabular data:
{{
  "companies": [
    {{
      "name": "Company A",
      "revenue": 125.4,
      "growth": 12.5,
      "employees": 5000,
      "source": "https://example.com/report"
    }}
  ]
}}

For historical events:
{{
  "events": [
    {{
      "name": "Battle of Midway",
      "date": "1942-06-04",
      "location": {{"lat": 28.2, "lng": -177.4}},
      "participants": ["United States", "Japan"],
      "casualties": {{"us": 307, "japan": 3057}},
      "outcome": "Decisive US victory",
      "source": "https://example.com/history"
    }}
  ]
}}

Extract ALL relevant data from both search snippets and scraped content above.
Tables from scraped content should be carefully parsed into structured formats.
Return ONLY valid JSON, no explanations.

Your extracted JSON:"""

        try:
            # Add timeout for the extraction call
            # response = await asyncio.wait_for(
            #     client.chat.completions.create(
            #         model="gpt-4o",
            #         messages=[{"role": "user", "content": extraction_prompt}],
            #         max_tokens=4000,
            #         temperature=0.3,
            #         timeout=60.0  # 60 second timeout for OpenAI API
            #     ),
            #     timeout=90.0  # 90 second overall timeout
            # )
            
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,  # INCREASED from 3000
            messages=[{"role": "user", "content": extraction_prompt}],
            timeout=60.0
             )
            
            # extracted_text = response.choices[0].message.content.strip()
            extracted_text = message.content[0].text
            
            # Clean JSON
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text[7:]
            if extracted_text.startswith("```"):
                extracted_text = extracted_text[3:]
            if extracted_text.endswith("```"):
                extracted_text = extracted_text[:-3]
            extracted_text = extracted_text.strip()
            
            extracted_data = json.loads(extracted_text)
            
            print(f"[DATA_EXTRACTOR] Successfully extracted structured data")
            print(f"[DATA_EXTRACTOR] Data keys: {list(extracted_data.keys())}")
            
            return extracted_data
            
        except asyncio.TimeoutError:
            print(f"[DATA_EXTRACTOR] Timeout during extraction (took >90s)")
            print(f"[DATA_EXTRACTOR] Continuing without structured data extraction")
            return {}
        except json.JSONDecodeError as e:
            print(f"[DATA_EXTRACTOR] JSON parse error: {e}")
            print(f"[DATA_EXTRACTOR] Response: {extracted_text[:200]}...")
            return {}
        except asyncio.CancelledError:
            print(f"[DATA_EXTRACTOR] Extraction cancelled")
            return {}
        except Exception as e:
            print(f"[DATA_EXTRACTOR] Error: {e}")
            return {}


class EnhancedHTMLAppGenerator:
    """
    Enhanced HTML App Generator with multi-stage research pipeline + web scraping
    """
    
    def __init__(
        self, 
        enable_reasoning_capture: bool = False,
        verbose: bool = False,
        max_search_queries: int = 5,
        max_urls_to_scrape: int = 5,
        scrape_timeout: int = 180,
        scrape_chunk_size: int = 400,
        scrape_concurrency: int = 10
    ):
        self.conversation_history: List[Dict] = []
        self.user_queries: List[str] = []
        self.iteration_count: int = 0
        self.current_html: Optional[str] = None
        
        # Components
        self.transformer = EnhancedQueryTransformer()
        self.searcher = WebSearcher()
        self.scraper = WebScraper()
        self.extractor = DataExtractor()
        
        # Settings
        self.enable_reasoning_capture = enable_reasoning_capture
        self.verbose = verbose
        self.max_search_queries = max_search_queries
        self.max_urls_to_scrape = max_urls_to_scrape
        self.scrape_timeout = scrape_timeout
        self.scrape_chunk_size = scrape_chunk_size
        self.scrape_concurrency = scrape_concurrency
        self.reasoning_logs = []
        
        # ✅ CALLBACK ATTRIBUTES FOR QUEUE-BASED ARCHITECTURE
        self.scraper_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
    
    def _log(self, step: str, message: str):
        """Log a step"""
        if self.enable_reasoning_capture:
            self.reasoning_logs.append({
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "message": message
            })
        
        if self.verbose or step in ["STAGE", "ERROR"]:
            print(f"[{step}] {message}")
    
    def develop_app(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict]] = None,
        use_multi_stage: bool = True,
        enable_scraping: bool = True,
        return_conversation: bool = True
    ) -> Union[str, Tuple[str, List[Dict]]]:
        """
        Main entry point - generates HTML app with optional multi-stage research and scraping
        
        Args:
            user_prompt: User's request
            conversation_history: Previous conversation for context
                                 Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            use_multi_stage: If True, uses full research pipeline (slower but better)
                            If False, uses simple single-stage (faster)
            enable_scraping: If True, scrapes top URLs for deeper content
            return_conversation: If True, returns (html, conversation_history) tuple
                               If False, returns just html string (default for backwards compatibility)
        
        Returns:
            If return_conversation=False: Complete HTML as string
            If return_conversation=True: Tuple of (html_string, updated_conversation_history)
        
        Example for iterative development:
            # First call
            html1, conversation = await generator.develop_app(
                "Create a weather dashboard",
                return_conversation=True
            )
            
            # Second call - pass conversation back
            html2, conversation = await generator.develop_app(
                "Add a 5-day forecast",
                conversation_history=conversation,
                return_conversation=True
            )
        """
        
        self._log("STAGE", f"Starting app development: {user_prompt[:100]}...")
        
        # Reconstruct conversation context if provided
        if conversation_history:
            self._reconstruct_context(conversation_history)
        
        self.user_queries.append(user_prompt)
        html = None
        # Generate HTML
        if use_multi_stage:
            # Full research pipeline with optional scraping
            yield {"type":"reasoning","content":"Developing app with a multi-stage pipeline"}
            
            for result in self._develop_with_research_pipeline(
                user_prompt,
                enable_scraping=enable_scraping
            ):
                if result.get("type") == "html":
                    html = result.get("content")
                else:
                    yield result
                 
            # html = await self._develop_with_research_pipeline(
            #     user_prompt,
            #     enable_scraping=enable_scraping
            # )
        else:
            # Simple single-stage (original behavior)
            html = self._develop_simple(user_prompt)
        
        # Return based on flag
        if return_conversation:
            yield {"type":"html","content":html}            
            # return html, self.get_conversation_history()
        else:
            yield {"type":"html","content":html}
            # return html
        yield {"type": "reasoning","content":"App development complete."}   
        yield {"type":"done","content":""}
    
    def get_conversation_history(self) -> List[Dict]:
        """
        Get the current conversation history
        
        Returns:
            List of conversation messages in format:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        return self.conversation_history.copy()
    
    def _reconstruct_context(self, history: List[Dict]):
        """Reconstruct conversation context from history"""
        
        self._log("CONTEXT", f"Reconstructing from {len(history)} messages")
        
        # Extract user queries
        self.user_queries = [
            msg["content"] for msg in history 
            if msg["role"] == "user"
        ]
        
        # Rebuild conversation history with summaries
        self.conversation_history = []
        
        # Add system prompt if not present
        if not any(msg.get("role") == "system" for msg in history):
            system_prompt = self._get_system_prompt(is_update=False)
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Reconstruct conversation
        for msg in history:
            if msg["role"] == "user":
                self.conversation_history.append(msg)
            elif msg["role"] == "assistant":
                content = msg["content"]
                if "<html" in content.lower() or "<!doctype" in content.lower():
                    self.current_html = content
                    # Add summary instead of full HTML
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": "Generated HTML app with requested features."
                    })
                else:
                    self.conversation_history.append(msg)
        
        self._log("CONTEXT", f"Has existing HTML: {self.current_html is not None}")
    
    def _generate_research_summary(
    self,
    user_query: str,
    search_results: Dict[str, List[Dict]],
    scraped_results: List[Dict],
    structured_data: Dict,
    final_markdown: str
    ) -> str:
        """
        Generate an analytical summary explaining the thought process:
        - What patterns were discovered in the sources
        - How different pieces of information connected
        - What insights emerged from synthesis
        - How the final report structure evolved from the data
        """
        
        # Build context about what was found
        successful_scrapes = [s for s in scraped_results if not s.get('error')]
        
        # Sample key content from sources
        source_insights = []
        for i, scrape in enumerate(successful_scrapes[:5], 1):  # Top 5 sources
            insight = {
                'url': scrape['url'],
                'key_content': scrape.get('best_chunk', '')[:1000],
                'tables_found': scrape.get('tables_count', 0),
                'relevance': scrape.get('score', 0)
            }
            source_insights.append(insight)
        
        # Sample structured data insights
        data_sample = {}
        if structured_data:
            for key in list(structured_data.keys())[:5]:
                data_sample[key] = str(structured_data[key])[:500]
        
        # Get report structure (headers only)
        report_headers = []
        for line in final_markdown.split('\n'):
            if line.startswith('##'):
                report_headers.append(line.strip())
        
        prompt = f"""You are analyzing a research and report generation process. Explain the ANALYTICAL THOUGHT PROCESS - not statistics, but how information was interpreted, connected, and synthesized.

    USER'S QUESTION:
    "{user_query}"

    SOURCES DISCOVERED:
    {chr(10).join([f'''
    Source {i+1}: {insight['url']}
    Relevance Score: {insight['relevance']:.2f}
    Key Content Found:
    {insight['key_content']}
    Tables: {insight['tables_found']}
    ---''' for i, insight in enumerate(source_insights)])}

    STRUCTURED DATA EXTRACTED:
    {json.dumps(data_sample, indent=2)}

    FINAL REPORT STRUCTURE:
    {chr(10).join(report_headers[:15])}

    YOUR TASK:
    Write a 3-4 paragraph narrative explaining the ANALYTICAL THOUGHT PROCESS:

    **Paragraph 1 - Discovery & Pattern Recognition:**
    What key themes, patterns, or data points emerged from the sources? What was significant about what we found? How did different sources complement or contradict each other?

    **Paragraph 2 - Synthesis & Connections:**
    How were different pieces of information connected together? What insights emerged from comparing or combining data from multiple sources? What relationships or trends became apparent?

    **Paragraph 3 - Report Structure Decisions:**
    Why was the report organized this way? How did the data inform which sections to create? What was the logic behind presenting information in this order?

    **Paragraph 4 - Value & Insights:**
    What key insights or conclusions emerged that weren't obvious from any single source? How does the synthesized report provide more value than the raw sources?

    Write as if you're explaining your reasoning to a colleague. Be specific about what you learned from the data and how it shaped your analysis. Use phrases like:
    - "The data revealed that..."
    - "By comparing X with Y, we discovered..."
    - "This pattern suggested..."
    - "The most significant finding was..."
    - "Connecting these sources showed..."

    DO NOT just list what was found. EXPLAIN the thinking process behind analysis and synthesis.

    Generate the analytical summary:"""

        try:
            # response = await client.chat.completions.create(
            #     model="gpt-4o",  # Use full model for better reasoning
            #     messages=[
            #         {
            #             "role": "system", 
            #             "content": "You are an expert analyst explaining complex research processes. You articulate how raw data becomes insights through analytical thinking, pattern recognition, and synthesis."
            #         },
            #         {"role": "user", "content": prompt}
            #     ],
            #     max_tokens=1500,
            #     temperature=0.7
            # )
            
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
         
            message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,  # INCREASED from 3000
            system="You are an expert analyst explaining complex research processes. You articulate how raw data becomes insights through analytical thinking, pattern recognition, and synthesis.",
            messages=[                    
                    {"role": "user", "content": prompt}
                ],
            )
            summary = message.content[0].text
            
            return summary
            
        except Exception as e:
            self._log("ERROR", f"Failed to generate analytical summary: {e}")
            return f"Unable to generate analytical summary: {e}"
        
        
    def _develop_with_research_pipeline(
        self,
        user_prompt: str,
        enable_scraping: bool = True
    ) -> str:
        """
        Full multi-stage research pipeline with web scraping
        
        Stages:
        1. Query transformation → multiple search queries
        2. Execute all searches → gather raw data
        3. Scrape top URLs → extract deep content and tables (QUEUE-BASED OR STANDALONE)
        4. Extract structured data → parse into JSON
        5. Generate HTML → use rich context
        6. Generate Research Summary → analytical thought process
        """
        
        # ========================================================================
        # STAGE 1: Query Transformation
        # ========================================================================
        self._log("STAGE", "=== STAGE 1: Query Transformation ===")
        
        start = datetime.now
        
        transform_result = None
        
        for result in self.transformer.get_transformed_query(
            user_prompt,
            self.user_queries[:-1]
        ):
            if result.get("type") == "transformed_query":
                yield {"type":"reasoning","content":result.get("content")}
            
            if result.get("type") == "transformer_output":
                transform_result = result.get("content")
        
        # Validate transform_result
        if not transform_result:
            print("[ERROR] Transformer returned None, using defaults")
            transform_result = {
                "web_search_needed": True,
                "search_queries": [user_prompt],
                "data_extraction_needed": False,
                "data_types": []
            }
        
        web_search_needed = transform_result['web_search_needed']
        search_queries = transform_result['search_queries'][:self.max_search_queries]
        data_types = transform_result.get('data_types', [])
        
        self._log("TRANSFORM", f"Web search needed: {web_search_needed}")
        self._log("TRANSFORM", f"Search queries: {len(search_queries)}")
        
        # Early exit if no search needed
        if not web_search_needed or not search_queries:
            self._log("STAGE", "No research needed, generating directly")
            yield {"type": "reasoning","content":"Developing report..."}
        
            from iterative_html_generator import develop_html
            html = develop_html(user_prompt, {}, [], {})
            # html = self._generate_html(user_prompt, {}, [], {})
            yield {"type":"html","content":html}
            return
        
        # ========================================================================
        # STAGE 2: Execute Web Searches
        # ========================================================================
        self._log("STAGE", f"=== STAGE 2: Executing {len(search_queries)} Searches ===")
        
        all_search_results = {}
        all_urls = []
        # search_queries = search_queries[1:]  # Skip first query (usually too broad)
        
        for i, query in enumerate(search_queries, 1):
            self._log("SEARCH", f"[{i}/{len(search_queries)}] {query}")
            
            results = self.searcher.search_google(query, num_results=10)
            all_search_results[query] = results
            
            currentUrls = []
            temp = []
            # Collect URLs for scraping
            for result in results:
                if result['link'] not in all_urls:
                    temp.append(result['link'])
                    currentUrls.append(result['link'])
            
            all_urls.extend(temp[0:5])
            
            content = {"transformed_query":query,"urls":currentUrls}
            yield {"type":"sources","content":content}
            
            self._log("SEARCH", f"  Found {len(results)} results")
            
            # Small delay to avoid rate limits
            if i < len(search_queries):
                import time
                time.sleep(0.3)
        
        yield {"type": "reasoning","content":f"found {len(all_urls)} sources..."}
        
        # ========================================================================
        # STAGE 3: Scrape URLs (QUEUE-BASED OR STANDALONE MODE)
        # ========================================================================
        scraped_results = []
        
        if enable_scraping and all_urls:
            self._log("STAGE", f"=== STAGE 3: Scraping Top {min(len(all_urls), self.max_urls_to_scrape)} URLs ===")
            yield {"type": "reasoning","content":f"performing deep analysis... "}
                
            urls_to_scrape = all_urls
            
            self._log("SCRAPER", f"Scraping {len(urls_to_scrape)} URLs...")
            for url in urls_to_scrape:
                self._log("SCRAPER", f"  - {url}")
            
            primary_query = search_queries[0] if search_queries else user_prompt
            
            # MODE 1: Queue-based (if callback is injected by tasks.py)
            if self.scraper_callback:
                print("[DEEP_SEARCH] Using queue-based scraper callback")
                try:
                    # Call the injected callback (LLM worker will send to scraper queue)
                    scraped_results = self.scraper_callback(
                        urls_to_scrape,
                        primary_query,
                        user_prompt  # original_query
                    )
                    
                    if scraped_results:
                        successful_scrapes = [s for s in scraped_results if not s.get('error')] 
                        print(f"[DEEP_SEARCH] Received {len(successful_scrapes)}/{len(scraped_results)} successful scrapes")
                        
                        for scrape in successful_scrapes:
                            self._log("SCRAPER", 
                                f"  {scrape['url'][:60]}... "
                                f"(score: {scrape['score']:.2f}, "
                                f"tables: {scrape['tables_count']}, "
                                f"words: {scrape['word_count']})")
                    else:
                        print("[DEEP_SEARCH] ⚠️ Scraper callback returned empty results")
                        
                except Exception as e:
                    print("=" * 80)
                    print(f"[DEEP_SEARCH] ❌ Error calling scraper callback: {e}")
                    print("=" * 80)
                    import traceback
                    traceback.print_exc()
                    scraped_results = []
            
            # MODE 2: Standalone (direct scraper call)
            else:
                print("[DEEP_SEARCH] Using standalone scraper (direct call)")
                try:
                    scraped_results = self.scraper.scrape_urls(
                        urls_to_scrape,
                        primary_query,
                        timeout=self.scrape_timeout,
                        chunk_size=self.scrape_chunk_size,
                        concurrency=self.scrape_concurrency
                    )
                    
                    successful_scrapes = [s for s in scraped_results if not s.get('error')]
                    self._log("SCRAPER", f"Successfully scraped {len(successful_scrapes)}/{len(scraped_results)} URLs")
                    
                    for scrape in successful_scrapes:
                        self._log("SCRAPER", 
                            f"  {scrape['url'][:60]}... "
                            f"(score: {scrape['score']:.2f}, "
                            f"tables: {scrape['tables_count']}, "
                            f"words: {scrape['word_count']})")
                            
                except Exception as e:
                    print(f"[DEEP_SEARCH] ❌ Error in standalone scraper: {e}")
                    import traceback
                    traceback.print_exc()
                    scraped_results = []
        else:
            self._log("STAGE", "=== STAGE 3: Skipping Web Scraping ===")
        
        # ========================================================================
        # STAGE 4: Extract Structured Data
        # ========================================================================
        stage_num = 4 if enable_scraping else 3
        self._log("STAGE", f"=== STAGE {stage_num}: Extracting Structured Data ===")
        
        try:
            yield {"type": "reasoning","content":f"developing assets..."}
            structured_data = self.extractor.extract_structured_data(
                all_search_results,
                scraped_results,
                data_types,
                user_prompt
            )
        except Exception as e:
            self._log("ERROR", f"Data extraction failed: {e}")
            self._log("WARNING", "Continuing without structured data")
            structured_data = {}
        
        # ========================================================================
        # STAGE 5: Generate HTML
        # ========================================================================
        stage_num += 1
        self._log("STAGE", f"=== STAGE {stage_num}: Generating HTML ===")
        
        # from iterative_html_generator import develop_html
        # html = develop_html(user_prompt,
        #     all_search_results,
        #     scraped_results,
        #     structured_data)
        
        html = self._generate_html(
            user_prompt,
            all_search_results,
            scraped_results,
            structured_data
        )
        
        self._log("COMPLETE", f"Generated {len(html)} characters")
        yield {"type":"html","content":html}
        
        # ========================================================================
        # STAGE 6: Generate Research Analysis Summary
        # ========================================================================
        self._log("STAGE", "=== Generating Research Analysis Summary ===")
        yield {"type": "reasoning", "content": "Analyzing research thought process..."}
        
        try:
            analytical_summary = self._generate_research_summary(
                user_prompt,
                all_search_results,
                scraped_results,
                structured_data,
                html
            )
            
            yield {"type": "analysis_summary", "content": analytical_summary}
        except Exception as e:
            self._log("ERROR", f"Failed to generate analytical summary: {e}")
            yield {"type": "analysis_summary", "content": f"Unable to generate summary: {e}"}
            
    def _develop_simple(self, user_prompt: str) -> str:
        """Simple single-stage generation (original behavior)"""
        
        # Use old transformer interface
        # from enhanced_query_transformer import QueryTransformer
        
        transform_result = self.transformer.get_transformed_query(
            user_prompt,
            self.user_queries[:-1]
        )
        
        search_results = {}
        scraped_results = []
        structured_data = {}
        
        if transform_result['web_search_needed'] and transform_result['search_query']:
            query = transform_result['search_query']
            results =  self.searcher.search_google(query, num_results=5)
            search_results[query] = results
        
        return  self._generate_html(
            user_prompt,
            search_results,
            scraped_results,
            structured_data
        )
    
#     def _generate_html(
#         self,
#         user_query: str,
#         search_results: Dict[str, List[Dict]],
#         scraped_results: List[Dict],
#         structured_data: Dict
#     ) -> str:
#         """
#         Generate HTML with comprehensive context including scraped data
#         """
        
#         is_update = self.current_html is not None
        
#         # Build search context string
#         search_context = ""
#         if search_results:
#             search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
#             for query, results in search_results.items():
#                 search_context += f"\nQuery: {query}\n"
#                 for i, result in enumerate(results, 1):
#                     search_context += f"\n{i}. {result['title']}\n"
#                     search_context += f"   URL: {result['link']}\n"
#                     search_context += f"   Snippet: {result['snippet']}\n"
        
#         # Build scraped content context
#         scraped_context = ""
#         if scraped_results:
#             scraped_context = "\n\n=== SCRAPED WEB CONTENT (FULL DEPTH) ===\n"
#             scraped_context += "This is the complete content extracted from web pages.\n"
            
#             successful_scrapes = [s for s in scraped_results if not s.get('error')]
            
#             for i, scrape in enumerate(successful_scrapes, 1):
#                 scraped_context += f"\n--- Source {i}: {scrape['url']} ---\n"
#                 scraped_context += f"Relevance Score: {scrape['score']:.2f}\n"
#                 scraped_context += f"Word Count: {scrape['word_count']}\n"
                
#                 # Add best chunk
#                 if scrape.get('best_chunk'):
#                     scraped_context += f"\nMost Relevant Content:\n"
#                     scraped_context += "```\n"
#                     scraped_context += scrape['best_chunk'][:3000]  # Include more context
#                     if len(scrape['best_chunk']) > 3000:
#                         scraped_context += "\n... (truncated)"
#                     scraped_context += "\n```\n"
                
#                 # Add tables
#                 if scrape.get('tables') and scrape['tables_count'] > 0:
#                     scraped_context += f"\nExtracted Tables ({scrape['tables_count']} total):\n"
#                     for j, table in enumerate(scrape['tables'], 1):
#                         scraped_context += f"\nTable {j}:\n"
#                         scraped_context += "```json\n"
#                         scraped_context += json.dumps(table, indent=2)[:2000]
#                         if len(json.dumps(table)) > 2000:
#                             scraped_context += "\n... (truncated)"
#                         scraped_context += "\n```\n"
        
#         # Build structured data context
#         structured_context = ""
#         if structured_data:
#             structured_context = "\n\n=== EXTRACTED STRUCTURED DATA ===\n"
#             structured_context += json.dumps(structured_data, indent=2)
#             structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your app."
        
#         # Get system prompt
#         system_prompt = self._get_system_prompt(is_update)
        
#         # Build user prompt
#         if is_update:
#             user_prompt = f"""Update the following HTML application based on this request:

# USER REQUEST: {user_query}

# CURRENT HTML APPLICATION:
# {self.current_html}
# {search_context}
# {scraped_context}
# {structured_context}

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT contains full-depth article content and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values parsed from all sources
# 3. Use the scraped tables directly - they contain structured data ready for visualization
# 4. The best_chunk field contains the most relevant text content from each page
# 5. Create a rich, data-driven application with real values, not templates
# 6. Include source citations with clickable URLs
# 7. If tables are present, create interactive visualizations (charts, sortable tables, etc.)
# 8. **CRITICAL: Include text summaries and commentary from the scraped content**
# 9. **DO NOT just show tables/charts - include the actual article text and insights**
# 10. **Create narrative sections that explain the data using the scraped text**

# CONTENT REQUIREMENTS:
# - Include a summary section with key insights from the scraped articles
# - Add commentary and analysis text from the sources
# - Create narrative descriptions alongside visualizations
# - Use the hundreds of words from best_chunk - don't waste them!
# - Include quotes or key points from the scraped content
# - Add context sections that explain what the data means

# EXAMPLE STRUCTURE:
# - Executive Summary (from scraped content)
# - Key Insights (from article text)
# - Data Visualizations (from tables)
# - Detailed Analysis (from best_chunk content)
# - Source References (with links)

# Generate the COMPLETE updated HTML application (output ONLY the HTML):"""
#         else:
#             user_prompt = f"""Create a self-contained HTML application based on this request:

# USER REQUEST: {user_query}
# {search_context}
# {scraped_context}
# {structured_context}

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT provides full-depth article text and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values from all sources
# 3. Tables from scraping are pre-structured - use them directly in your app
# 4. The best_chunk field contains the most relevant excerpts from each source
# 5. Create comprehensive, data-rich visualizations using the provided data
# 6. Include interactive features to explore the scraped content
# 7. Add source attribution with clickable links to original URLs
# 8. If tables are present, create charts, graphs, or interactive tables
# 9. Use actual data values, not placeholder or dummy data
# 10. **CRITICAL: Include text summaries, commentary, and analysis from scraped content**
# 11. **DO NOT just show tables/charts - include the article text and insights**
# 12. **Create narrative sections that explain and contextualize the data**
# 13. 100% OF DATA SENT MUST BE INCLUDED IN THE HTML APP

# CONTENT REQUIREMENTS:
# - Include a summary/overview section with key insights from the scraped articles
# - Add commentary, analysis, and explanatory text from the sources
# - Create narrative descriptions alongside all visualizations
# - All SVG and Tables data must be preserved
# - Use the hundreds of words from best_chunk content - this is valuable information!
# - Include relevant quotes, key points, or highlights from scraped articles
# - Add context sections that explain trends, patterns, or what the data means
# - Make the app informative and educational, not just visual

# EXAMPLE STRUCTURE:
# 1. Executive Summary (synthesized from scraped article content)
# 2. Key Findings & Insights (from article text and analysis)
# 3. Interactive Visualizations (from tables + explanatory text)
# 4. Detailed Analysis (from best_chunk content with commentary)
# 5. Additional Context (trends, patterns, explanations from articles)
# 6. Sources & References (with clickable links)

# The scraped content contains hundreds of words of valuable information - USE IT ALL!
# Don't just extract numbers for charts - include the surrounding analysis and commentary.

# Generate the COMPLETE HTML application (output ONLY the HTML):"""
        
#         # Add to conversation history
#         if not self.conversation_history:
#             self.conversation_history.append({
#                 "role": "system",
#                 "content": system_prompt
#             })
        
#         self.conversation_history.append({
#             "role": "user",
#             "content": user_prompt
#         })
        
#         # Generate with GPT-4o
#         start_time = datetime.now()
        
#         response = await client.chat.completions.create(
#             model="gpt-4o",
#             messages=self.conversation_history,
#             max_tokens=4000,
#             temperature=0.7
#         )
        
#         duration = (datetime.now() - start_time).total_seconds()
        
#         if self.verbose:
#             self._log("API", f"Response in {duration:.2f}s")
#             if hasattr(response, 'usage'):
#                 self._log("TOKENS", 
#                     f"Prompt: {response.usage.prompt_tokens}, "
#                     f"Completion: {response.usage.completion_tokens}")
        
#         html_content = response.choices[0].message.content.strip()
        
#         # Clean up
#         if html_content.startswith("```html"):
#             html_content = html_content[7:]
#         elif html_content.startswith("```"):
#             html_content = html_content[3:]
#         if html_content.endswith("```"):
#             html_content = html_content[:-3]
#         html_content = html_content.strip()
        
#         # Validate
#         if not html_content.lower().startswith("<!doctype") and not html_content.lower().startswith("<html"):
#             self._log("WARNING", "Generated content doesn't look like HTML")
#             html_content = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Generated App</title>
# </head>
# <body>
# {html_content}
# </body>
# </html>"""
        
#         # Store state
#         self.current_html = html_content
        
#         # Add summary to conversation
#         summary = f"Generated HTML app with requested features."
#         if search_results:
#             total_results = sum(len(r) for r in search_results.values())
#             summary += f" Used {len(search_results)} search queries with {total_results} results."
#         if scraped_results:
#             successful = len([s for s in scraped_results if not s.get('error')])
#             total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
#             summary += f" Scraped {successful} pages with {total_tables} tables extracted."
#         if structured_data:
#             summary += f" Extracted structured data with {len(structured_data)} data categories."
        
#         self.conversation_history.append({
#             "role": "assistant",
#             "content": summary
#         })
        
#         return html_content
#     def _generate_html_extended_output(
#         self,
#         user_query: str,
#         search_results: Dict[str, List[Dict]],
#         scraped_results: List[Dict],
#         structured_data: Dict
#     ) -> str:
#         """
#         Generate HTML with comprehensive context including scraped data.
#         ENFORCES: SVG-only visualizations, NO client-side JS for charts.
#         ENFORCES: 100% data utilization - every table, every insight must be included.
#         """
        
#         is_update = self.current_html is not None
        
#         # Build search context string
#         search_context = ""
#         if search_results:
#             search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
#             for query, results in search_results.items():
#                 search_context += f"\nQuery: {query}\n"
#                 for i, result in enumerate(results, 1):
#                     search_context += f"\n{i}. {result['title']}\n"
#                     search_context += f"   URL: {result['link']}\n"
#                     search_context += f"   Snippet: {result['snippet']}\n"
        
#         # Build scraped content context
#         scraped_context = ""
#         if scraped_results:
#             scraped_context = "\n\n=== SCRAPED WEB CONTENT (FULL DEPTH) ===\n"
#             scraped_context += "This is the complete content extracted from web pages.\n"
            
#             successful_scrapes = [s for s in scraped_results if not s.get('error')]
            
#             for i, scrape in enumerate(successful_scrapes, 1):
#                 scraped_context += f"\n--- Source {i}: {scrape['url']} ---\n"
#                 scraped_context += f"Relevance Score: {scrape['score']:.2f}\n"
#                 scraped_context += f"Word Count: {scrape['word_count']}\n"
                
#                 # Add best chunk
#                 if scrape.get('best_chunk'):
#                     scraped_context += f"\nMost Relevant Content:\n"
#                     scraped_context += "```\n"
#                     scraped_context += scrape['best_chunk'][:3000]
#                     if len(scrape['best_chunk']) > 3000:
#                         scraped_context += "\n... (truncated)"
#                     scraped_context += "\n```\n"
                
#                 # Add tables
#                 if scrape.get('tables') and scrape['tables_count'] > 0:
#                     scraped_context += f"\nExtracted Tables ({scrape['tables_count']} total):\n"
#                     for j, table in enumerate(scrape['tables'], 1):
#                         scraped_context += f"\nTable {j}:\n"
#                         scraped_context += "```json\n"
#                         scraped_context += json.dumps(table, indent=2)[:2000]
#                         if len(json.dumps(table)) > 2000:
#                             scraped_context += "\n... (truncated)"
#                         scraped_context += "\n```\n"
        
#         # Build structured data context
#         structured_context = ""
#         if structured_data:
#             structured_context = "\n\n=== EXTRACTED STRUCTURED DATA ===\n"
#             structured_context += json.dumps(structured_data, indent=2)
#             structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your app."
        
#         # Get system prompt
#         system_prompt = self._get_system_prompt_svg_only(is_update)
        
#         # Build user prompt
#         if is_update:
#             user_prompt = f"""Update the following HTML application based on this request:

# USER REQUEST: {user_query}

# CURRENT HTML APPLICATION:
# {self.current_html}
# {search_context}
# {scraped_context}
# {structured_context}

# 🚨 CRITICAL REQUIREMENTS 🚨

# **1. SVG-ONLY VISUALIZATION RULE:**
# - ❌ FORBIDDEN: Chart.js, D3.js, Plotly, Canvas, or ANY JavaScript charting library
# - ✅ REQUIRED: Create ALL charts as embedded SVG elements directly in HTML
# - Every data point must be manually plotted in SVG
# - Example: For 18 temperature readings, create 18 SVG circles/bars/lines
# - SVG must be production-ready and fully rendered (no placeholders)

# **2. 100% DATA UTILIZATION RULE:**
# - You have received {len(successful_scrapes)} scraped pages with {sum(s.get('tables_count', 0) for s in scraped_results)} tables total
# - EVERY SINGLE TABLE must be converted to BOTH:
#   a) An HTML table with ALL rows
#   b) An SVG chart visualizing the same data
# - EVERY paragraph from best_chunk must be included as explanatory text
# - NO DATA CAN BE OMITTED - if you received 73 tables, output must have 73 tables + 73 SVG charts

# **3. EXHAUSTIVE CONTENT REQUIREMENTS:**
# - Include ALL text from best_chunk fields (hundreds/thousands of words)
# - Create narrative sections explaining every dataset
# - Add analysis and commentary for every visualization
# - Include source attribution for every piece of data
# - Create executive summaries synthesizing all information

# **4. NO SHORTCUTS ALLOWED:**
# - ❌ NO "... (more data)" or "Additional rows omitted"
# - ❌ NO truncation of tables or charts
# - ❌ NO placeholder data when real data exists
# - ❌ NO comments like "<!-- data continues -->"
# - ✅ EVERY row of EVERY table must be present
# - ✅ EVERY data point must be visualized in SVG

# **DATA INVENTORY:**
# {f"- Search Results: {sum(len(r) for r in search_results.values())} results" if search_results else ""}
# {f"- Scraped Pages: {len([s for s in scraped_results if not s.get('error')])} pages" if scraped_results else ""}
# {f"- Total Tables: {sum(s.get('tables_count', 0) for s in scraped_results)} tables" if scraped_results else ""}
# {f"- Total Words: {sum(s.get('word_count', 0) for s in scraped_results)} words" if scraped_results else ""}
# {f"- Structured Data Keys: {list(structured_data.keys())}" if structured_data else ""}

# **YOUR TASK:** Use 100% of this data. Create a comprehensive HTML application where:
# 1. Every table → HTML table + SVG chart
# 2. Every text insight → Explanatory section
# 3. Every data point → Visualized and explained
# 4. Zero data loss

# Generate the COMPLETE updated HTML application (output ONLY the HTML):"""
#         else:
#             # Count data for accountability
#             num_scraped = len([s for s in scraped_results if not s.get('error')])
#             num_tables = sum(s.get('tables_count', 0) for s in scraped_results)
#             num_words = sum(s.get('word_count', 0) for s in scraped_results)
            
#             user_prompt = f"""Create a self-contained HTML application based on this request:

# USER REQUEST: {user_query}
# {search_context}
# {scraped_context}
# {structured_context}

# 🚨 CRITICAL REQUIREMENTS 🚨

# **1. SVG-ONLY VISUALIZATION RULE:**
# - ❌ ABSOLUTELY FORBIDDEN: Chart.js, D3.js, Plotly.js, Highcharts, or ANY JavaScript charting library
# - ❌ ABSOLUTELY FORBIDDEN: <canvas> elements for charts
# - ❌ ABSOLUTELY FORBIDDEN: External chart rendering of any kind
# - ✅ MANDATORY: Create ALL charts as embedded <svg> elements directly in HTML
# - ✅ MANDATORY: Manually plot every single data point in SVG coordinates
# - ✅ MANDATORY: Complete, production-ready SVG with no placeholders

# **SVG CREATION REQUIREMENTS:**
# - For line charts: Use <polyline> or <path> with ALL data points
# - For bar charts: Use <rect> for EACH bar, no shortcuts
# - For scatter plots: Use <circle> for EACH point
# - Include axes: <line> elements for x-axis and y-axis
# - Include labels: <text> elements for ALL labels and values
# - Include title: <text> element centered at top
# - Use proper viewBox for responsiveness
# - Example: If you have 24 hourly temperatures, create 24 data points in SVG

# **2. 100% DATA UTILIZATION RULE:**

# YOU HAVE RECEIVED:
# {f"📊 {num_tables} tables from {num_scraped} web pages" if scraped_results else "No scraped data"}
# {f"📝 {num_words} words of content" if scraped_results else ""}
# {f"🔍 {sum(len(r) for r in search_results.values())} search results" if search_results else ""}
# {f"📋 Structured data with keys: {list(structured_data.keys())}" if structured_data else ""}

# **MANDATORY DATA USAGE:**
# ✅ EVERY TABLE must appear as:
#    1. Complete HTML <table> with ALL rows (no truncation)
#    2. SVG visualization showing the same data
#    3. Analysis paragraph explaining the data

# ✅ EVERY paragraph from best_chunk must be included as text content

# ✅ EVERY search result must be referenced or linked

# ✅ ALL structured data must be displayed/visualized

# **3. EXHAUSTIVE CONTENT STRUCTURE:**

# Your HTML MUST include:

# **A. Executive Summary Section:**
# - Synthesize insights from ALL scraped content
# - 3-5 paragraphs covering key findings
# - Pull from best_chunk text

# **B. Key Findings Section:**
# - Bullet list with 5-10 major insights
# - Each insight backed by data
# - Include numbers/statistics

# **C. Data Visualization Section:**
# FOR EACH TABLE you received:
# - Heading: "Dataset X: [descriptive name]"
# - HTML table with ALL rows and columns
# - SVG chart visualizing the data (appropriate chart type)
# - Analysis paragraph explaining patterns/trends

# **D. Detailed Analysis Section:**
# - Use ALL remaining text from best_chunk
# - Create subsections for different topics
# - Include quotes or key excerpts
# - Add commentary and interpretation

# **E. Additional Context Section:**
# - Trends, patterns, implications
# - Comparisons across datasets
# - Future outlook or predictions

# **F. Sources & References Section:**
# - Clickable links to ALL source URLs
# - Brief description of each source

# **4. SVG CHART EXAMPLES:**

# **Temperature Line Chart (18 hours of data):**
# ```html
# <svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
#   <text x="400" y="30" text-anchor="middle" font-size="18" font-weight="bold">Temperature Over Time</text>
#   <line x1="50" y1="350" x2="750" y2="350" stroke="black" stroke-width="2"/>
#   <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
#   <polyline points="50,290 90,285 130,280 170,275 210,270 250,265 290,260 330,255 370,260 410,265 450,270 490,275 530,280 570,285 610,290 650,295 690,300 730,305" 
#             fill="none" stroke="#FF5722" stroke-width="3"/>
#   <circle cx="50" cy="290" r="4" fill="#FF5722"/>
#   <circle cx="90" cy="285" r="4" fill="#FF5722"/>
#   <!-- ... create circle for ALL 18 points -->
#   <text x="50" y="370" text-anchor="middle" font-size="10">6am</text>
#   <text x="90" y="370" text-anchor="middle" font-size="10">7am</text>
#   <!-- ... create label for ALL 18 hours -->
#   <text x="40" y="295" text-anchor="end" font-size="11">12°C</text>
#   <text x="40" y="265" text-anchor="end" font-size="11">15°C</text>
# </svg>
# ```

# **Bar Chart (10 categories):**
# ```html
# <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
#   <text x="300" y="30" text-anchor="middle" font-size="18" font-weight="bold">Sales by Category</text>
#   <line x1="50" y1="350" x2="550" y2="350" stroke="black" stroke-width="2"/>
#   <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
#   <rect x="60" y="200" width="40" height="150" fill="#2196F3"/>
#   <rect x="110" y="180" width="40" height="170" fill="#2196F3"/>
#   <rect x="160" y="160" width="40" height="190" fill="#2196F3"/>
#   <!-- ... create rect for ALL 10 categories -->
#   <text x="80" y="370" text-anchor="middle" font-size="10">Cat 1</text>
#   <text x="130" y="370" text-anchor="middle" font-size="10">Cat 2</text>
#   <!-- ... create label for ALL 10 categories -->
# </svg>
# ```

# **5. NO SHORTCUTS CHECKLIST:**

# Before submitting, verify:
# □ Zero Chart.js / D3.js / Canvas usage
# □ All charts are pure SVG elements
# □ Every table has corresponding SVG chart
# □ All table rows included (no "..." or truncation)
# □ All best_chunk text used as content
# □ Executive summary synthesizes all data
# □ Analysis sections explain every dataset
# □ Sources section lists all URLs
# □ No placeholder data when real data exists
# □ HTML is self-contained (CSS in <style>)

# **6. STYLING REQUIREMENTS:**

# Use modern CSS (in <style> tag):
# - Gradient backgrounds
# - Card-based layouts with shadows
# - Professional color scheme
# - Responsive design (mobile-friendly)
# - Smooth transitions and hover effects
# - Beautiful typography
# - Proper spacing and whitespace

# **7. CONTENT-TO-VISUALIZATION RATIO:**

# Aim for 60% explanatory text, 40% visualizations:
# - Don't just show charts - explain what they mean
# - Don't just list data - interpret and analyze
# - Add narrative flow between sections
# - Make it educational and informative

# **8. QUALITY STANDARDS:**

# This is PRODUCTION-GRADE output:
# - No bugs, no broken SVG
# - Professional appearance
# - Accessible (proper semantic HTML)
# - Well-organized and easy to navigate
# - Comprehensive and exhaustive

# Generate the COMPLETE HTML application using 100% of the provided data.
# Output ONLY the HTML (no explanations, no markdown code blocks)."""
        
#         # Add to conversation history
#         if not self.conversation_history:
#             self.conversation_history.append({
#                 "role": "system",
#                 "content": system_prompt
#             })
        
#         self.conversation_history.append({
#             "role": "user",
#             "content": user_prompt
#         })
        
#         # Generate with GPT-4o
#         start_time = datetime.now()
        
#         response = await client.chat.completions.create(
#             model="gpt-4o",
#             messages=self.conversation_history,
#             max_tokens=16000,  # Increased for exhaustive content
#             temperature=0.7
#         )
        
#         duration = (datetime.now() - start_time).total_seconds()
        
#         if self.verbose:
#             self._log("API", f"Response in {duration:.2f}s")
#             if hasattr(response, 'usage'):
#                 self._log("TOKENS", 
#                     f"Prompt: {response.usage.prompt_tokens}, "
#                     f"Completion: {response.usage.completion_tokens}")
        
#         html_content = response.choices[0].message.content.strip()
        
#         # Clean up
#         if html_content.startswith("```html"):
#             html_content = html_content[7:]
#         elif html_content.startswith("```"):
#             html_content = html_content[3:]
#         if html_content.endswith("```"):
#             html_content = html_content[:-3]
#         html_content = html_content.strip()
        
#         # Validate
#         if not html_content.lower().startswith("<!doctype") and not html_content.lower().startswith("<html"):
#             self._log("WARNING", "Generated content doesn't look like HTML")
#             html_content = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Generated App</title>
# </head>
# <body>
# {html_content}
# </body>
# </html>"""
        
#         # Validate no Chart.js usage
#         if any(lib in html_content.lower() for lib in ['chart.js', 'chartjs', 'd3.js', 'plotly']):
#             self._log("WARNING", "Detected JavaScript charting library - this violates SVG-only requirement")
        
#         # Store state
#         self.current_html = html_content
        
#         # Add summary to conversation
#         summary = f"Generated comprehensive HTML app with SVG visualizations."
#         if search_results:
#             total_results = sum(len(r) for r in search_results.values())
#             summary += f" Used {len(search_results)} search queries with {total_results} results."
#         if scraped_results:
#             successful = len([s for s in scraped_results if not s.get('error')])
#             total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
#             summary += f" Scraped {successful} pages with {total_tables} tables - all converted to HTML tables + SVG charts."
#         if structured_data:
#             summary += f" Utilized structured data with {len(structured_data)} categories."
        
#         self.conversation_history.append({
#             "role": "assistant",
#             "content": summary
#         })
        
#         return html_content

    def _generate_html(
        self,
        user_query: str,
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        structured_data: Dict
    ) -> str:
        """
        Generate HTML with comprehensive context including scraped data.
        Uses strategic prompting to avoid LLM refusal.
        """
        
        is_update = self.current_html is not None
        
        # Build search context string
        search_context = ""
        if search_results:
            search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
            for query, results in search_results.items():
                search_context += f"\nQuery: {query}\n"
                for i, result in enumerate(results, 1):
                    search_context += f"\n{i}. {result['title']}\n"
                    search_context += f"   URL: {result['link']}\n"
                    search_context += f"   Snippet: {result['snippet']}\n"
        
        # Build scraped content context
        scraped_context = ""
        if scraped_results:
            scraped_context = "\n\n=== SCRAPED WEB CONTENT (FULL DEPTH) ===\n"
            scraped_context += "This is the complete content extracted from web pages.\n"
            
            successful_scrapes = [s for s in scraped_results if not s.get('error')]
            
            for i, scrape in enumerate(successful_scrapes, 1):
                scraped_context += f"\n--- Source {i}: {scrape['url']} ---\n"
                scraped_context += f"Relevance Score: {scrape['score']:.2f}\n"
                scraped_context += f"Word Count: {scrape['word_count']}\n"
                
                # Add best chunk
                if scrape.get('best_chunk'):
                    scraped_context += f"\nMost Relevant Content:\n"
                    scraped_context += "```\n"
                    scraped_context += scrape['best_chunk'][:3000]
                    if len(scrape['best_chunk']) > 3000:
                        scraped_context += "\n... (truncated)"
                    scraped_context += "\n```\n"
                
                # Add tables
                if scrape.get('tables') and scrape['tables_count'] > 0:
                    scraped_context += f"\nExtracted Tables ({scrape['tables_count']} total):\n"
                    for j, table in enumerate(scrape['tables'], 1):
                        scraped_context += f"\nTable {j}:\n"
                        scraped_context += "```json\n"
                        scraped_context += json.dumps(table, indent=2)[:2000]
                        if len(json.dumps(table)) > 2000:
                            scraped_context += "\n... (truncated)"
                        scraped_context += "\n```\n"
        
        # Build structured data context
        structured_context = ""
        if structured_data:
            structured_context = "\n\n=== EXTRACTED STRUCTURED DATA ===\n"
            structured_context += json.dumps(structured_data, indent=2)
            structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your app."
        
        # Get system prompt
        system_prompt = self._get_system_prompt_strategic(is_update)
        
        # Build user prompt with STRATEGIC framing
        if is_update:
            user_prompt = f"""Update the following HTML application based on this request:

USER REQUEST: {user_query}

CURRENT HTML APPLICATION:
{self.current_html}
{search_context}
{scraped_context}
{structured_context}

YOUR TASK: Create a production-ready HTML application that uses the data provided above.

VISUALIZATION REQUIREMENTS:
- Use embedded SVG elements for ALL charts (no Chart.js, no Canvas)
- Create complete SVG charts with proper axes, labels, and data points
- For tables with data, create both: HTML table + SVG visualization

DATA USAGE REQUIREMENTS:
- Use all tables provided - convert each to HTML table + SVG chart
- Include text content from scraped sources in explanatory sections
- Create narrative sections that explain the data
- Add executive summary synthesizing key insights
- Include source links at the bottom

STRUCTURE YOUR HTML AS:
1. Header with title
2. Executive summary section
3. Key findings (bullet points)
4. Data sections (each with: heading, table, SVG chart, analysis text)
5. Sources section with links

STYLING:
- Modern, responsive design
- All CSS in <style> tag
- Professional color scheme
- Gradient backgrounds and shadows
- Mobile-friendly

OUTPUT: Complete, self-contained HTML file (DOCTYPE to closing html tag).
Begin your response with: <!DOCTYPE html>"""
        else:
            # Count data
            num_scraped = len([s for s in scraped_results if not s.get('error')])
            num_tables = sum(s.get('tables_count', 0) for s in scraped_results)
            
            user_prompt = f"""Create a comprehensive HTML application based on this request:

USER REQUEST: {user_query}

DATA PROVIDED:
{search_context}
{scraped_context}
{structured_context}

YOUR TASK: Build a beautiful, data-rich HTML application using the information above.

KEY REQUIREMENTS:

1. VISUALIZATIONS (IMPORTANT):
   - Create charts using SVG elements embedded in HTML
   - DO NOT use Chart.js, D3.js, or JavaScript charting libraries
   - Manually create each chart with <svg>, <rect>, <circle>, <line>, <polyline>, <text>
   - Example SVG bar chart:
     ```html
     <svg viewBox="0 0 600 400">
       <rect x="50" y="200" width="40" height="150" fill="#4CAF50"/>
       <rect x="100" y="180" width="40" height="170" fill="#4CAF50"/>
       <text x="70" y="370">Item 1</text>
     </svg>
     ```

2. DATA USAGE:
   - Process all {num_tables} tables from the {num_scraped} scraped pages
   - For each table: create HTML <table> + corresponding SVG chart
   - Include explanatory text from the scraped content
   - Synthesize insights in an executive summary

3. HTML STRUCTURE:
   ```
   - Header with title
   - Executive Summary (2-3 paragraphs synthesizing data)
   - Key Findings (5-10 bullet points)
   - Data Visualizations Section:
     * For each dataset:
       - Subheading
       - HTML table with data
       - SVG chart showing the data
       - Paragraph analyzing the data
   - Sources (clickable links)
   ```

4. STYLING:
   - Self-contained (all CSS in <style> tag)
   - Modern, professional design
   - Responsive (works on mobile)
   - Use gradients, shadows, cards
   - Professional color palette

5. OUTPUT FORMAT:
   - Complete HTML file from <!DOCTYPE html> to </html>
   - No explanations, no markdown code blocks
   - Production-ready code

Generate the complete HTML now. Start with: <!DOCTYPE html>"""
        
        # Add to conversation history
        # if not self.conversation_history:
        #     self.conversation_history.append({
        #         "role": "system",
        #         "content": system_prompt
        #     })
        
        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Generate with GPT-4o
        start_time = datetime.now()
        
        # response = await client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=self.conversation_history,
        #     max_tokens=16000,
        #     temperature=0.7
        # )
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        system_message = None
        filtered_messages = []
        for msg in self.conversation_history:
            if msg.get("role") == "system":
                system_message = msg.get("content")
            else:
                filtered_messages.append(msg)
            
        message = client.messages.create(
            model="claude-opus-4-20250514",
            system=system_prompt,
            max_tokens= 16000,  # Increased token limit
            messages=filtered_messages  ,
            
            # thinking={
            #     "type": "enabled",
            #     "budget_tokens": 10000  # Extra thinking tokens
            # },
        )
          
        duration = (datetime.now() - start_time).total_seconds()
        
        # if self.verbose:
        #     self._log("API", f"Response in {duration:.2f}s")
        #     if hasattr(response, 'usage'):
        #         self._log("TOKENS", 
        #             f"Prompt: {response.usage.prompt_tokens}, "
        #             f"Completion: {response.usage.completion_tokens}")
        
        # html_content = response.choices[0].message.content.strip()
        html_content = message.content[0].text
        
        # Clean up
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        elif html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()
        
        # Validate
        if not html_content.lower().startswith("<!doctype") and not html_content.lower().startswith("<html"):
            self._log("WARNING", "Generated content doesn't look like HTML")
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated App</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        # Validate no Chart.js usage
        if any(lib in html_content.lower() for lib in ['chart.js', 'chartjs', 'd3.js', 'plotly']):
            self._log("WARNING", "Detected JavaScript charting library - this violates SVG-only requirement")
        
        # Store state
        self.current_html = html_content
        
        # Add summary to conversation
        summary = f"Generated HTML app with SVG visualizations."
        if search_results:
            total_results = sum(len(r) for r in search_results.values())
            summary += f" Used {len(search_results)} search queries with {total_results} results."
        if scraped_results:
            successful = len([s for s in scraped_results if not s.get('error')])
            total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
            summary += f" Processed {successful} pages with {total_tables} tables."
        if structured_data:
            summary += f" Utilized structured data."
        
        self.conversation_history.append({
            "role": "assistant",
            "content": summary
        })
        
        return html_content
    
    
    def _get_system_prompt_strategic(self, is_update: bool) -> str:
        """Get strategic system prompt that doesn't overwhelm LLM"""
        
        base_rules = """You are an expert web developer who creates beautiful, comprehensive HTML applications.

CORE PRINCIPLES:
- You create production-ready, self-contained HTML applications
- You use the data provided to build informative, visual applications
- You create SVG charts manually (no JavaScript charting libraries)
- You organize content clearly with good structure
- You write clean, professional code

TECHNICAL STANDARDS:
- Self-contained: All CSS in <style> tag, minimal JS in <script> tag
- Responsive: Mobile-friendly design
- Modern: Gradients, shadows, professional styling
- Accessible: Semantic HTML, proper hierarchy
- Complete: From <!DOCTYPE html> to </html>

VISUALIZATION APPROACH:
- Create charts using SVG elements (<svg>, <rect>, <circle>, <line>, <polyline>, <text>)
- Avoid Chart.js, D3.js, or Canvas-based charting
- Build charts directly in HTML with proper axes and labels
- Make charts responsive using viewBox

CONTENT ORGANIZATION:
- Start with executive summary
- List key findings
- Present data with tables and charts
- Explain data with analysis text
- End with source references

You produce high-quality HTML that uses the provided data effectively."""

        if is_update:
            return base_rules + "\n\nYou will update an existing HTML application."
        else:
            return base_rules + "\n\nYou will create a new HTML application."
    
    def _get_system_prompt_svg_only(self, is_update: bool) -> str:
        """Get system prompt for SVG-only generation"""
        
        base_rules = """You are an expert web developer creating self-contained HTML applications.

🎯 CORE MISSION: Create exhaustive, data-rich HTML applications using 100% of provided data.

CRITICAL RULES:

**1. SVG-ONLY VISUALIZATION (STRICTLY ENFORCED):**
❌ You are FORBIDDEN from using:
   - Chart.js, D3.js, Plotly.js, Highcharts, or ANY JavaScript charting library
   - <canvas> elements for charts
   - External rendering or client-side chart generation
   - ANY code that says "new Chart()" or similar

✅ You MUST use:
   - Pure <svg> elements embedded directly in HTML
   - Manual plotting of every data point with SVG primitives
   - <rect>, <circle>, <line>, <polyline>, <path>, <text> elements
   - Complete, production-ready SVG with proper viewBox and styling

**2. 100% DATA UTILIZATION (STRICTLY ENFORCED):**
You will receive scraped data with tables and text content.
YOU MUST USE EVERY SINGLE PIECE:

✅ EVERY table → HTML <table> + SVG chart
✅ EVERY paragraph → Explanatory text section
✅ EVERY data point → Visualized and explained
✅ EVERY source → Cited and linked

❌ NO shortcuts like "... (more data)" or "see full data"
❌ NO truncation of tables
❌ NO omission of rows or columns
❌ NO placeholder data when real data exists

**3. EXHAUSTIVE CONTENT STRUCTURE:**
Create comprehensive sections:
- Executive Summary (synthesize all insights)
- Key Findings (bullet list of major points)
- Data Visualizations (EVERY table + SVG + analysis)
- Detailed Analysis (use ALL text content)
- Additional Context (trends, patterns, implications)
- Sources (all URLs with links)

**4. TECHNICAL REQUIREMENTS:**
✅ Self-contained (all CSS in <style>, minimal JS in <script>)
✅ Responsive design (mobile-friendly)
✅ Semantic HTML5
✅ Accessible (ARIA labels, proper hierarchy)
✅ Professional styling (gradients, shadows, modern UI)
✅ Production-ready quality

**5. SVG CHART QUALITY STANDARDS:**
Your SVG charts must be:
- Complete (all data points plotted)
- Professional (proper axes, labels, legends)
- Accurate (correct coordinate calculations)
- Styled (colors, fonts, proper spacing)
- Responsive (using viewBox)
- Properly sized and positioned

**6. CONTENT QUALITY STANDARDS:**
- Educational and informative (not just visual)
- Well-organized with clear hierarchy
- Narrative flow between sections
- Analysis and interpretation, not just data display
- Comprehensive coverage of all topics
- Professional writing quality

**7. NO EXCUSES:**
- "Data is too large" → Use it all anyway
- "Too many tables" → Create HTML table + SVG for each
- "Too much text" → Include it all in organized sections
- "Complex data" → Visualize it properly with SVG

The user has done hard work to gather this data.
Your job is to use 100% of it to create an exhaustive, beautiful application."""

        if is_update:
            return base_rules + "\n\n**MODE:** You will UPDATE an existing application. Preserve existing features while adding new ones."
        else:
            return base_rules + "\n\n**MODE:** You will CREATE a new application from scratch."
        
    def generate_report(
        self,
        user_query: str,
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        structured_data: Dict
    ) -> tuple[str, str]:
        """
        Generate both markdown and HTML reports.
        First generates markdown with all data, then converts to HTML.
        
        Returns:
            tuple: (markdown_content, html_content)
        """
        
        # Step 1: Generate comprehensive markdown report
        if self.verbose:
            self._log("REPORT", "Generating markdown report...")
        
        markdown_content = self._generate_html(
            user_query=user_query,
            search_results=search_results,
            scraped_results=scraped_results,
            structured_data=structured_data
        )
        
        if self.verbose:
            self._log("MARKDOWN", f"Generated {len(markdown_content)} characters")
        
        # Step 2: Convert markdown to stunning HTML
        if self.verbose:
            self._log("REPORT", "Converting markdown to HTML...")
        
        html_content =  self._generate_html_from_markdown(
            markdown_content=markdown_content
        )
        
        if self.verbose:
            self._log("HTML", f"Generated {len(html_content)} characters")
        
        return  html_content
    
    def _get_system_prompt(self, is_update: bool) -> str:
        """Get system prompt for generation"""
        
        base_rules = """You are an expert web developer creating self-contained HTML applications.

CRITICAL RULES:
1. Output ONLY complete HTML code - no explanations, no markdown
2. COMPLETELY SELF-CONTAINED: all CSS in <style>, all JS in <script>
3. Modern, professional, responsive design
4. Fully functional and production-ready
5. Cross-browser compatible

DATA USAGE RULES (MOST IMPORTANT):
6. If SCRAPED WEB CONTENT is provided:
   - This contains full article text and extracted tables
   - Tables are pre-structured JSON data ready for use
   - best_chunk contains the most relevant excerpts
   - Use this data directly in your JavaScript
   - Create visualizations from the scraped tables
   
7. If EXTRACTED STRUCTURED DATA is provided:
   - This is pre-parsed, ready-to-use JSON data
   - Use these EXACT values in your JavaScript
   - Example: data.countries["United States"].gdp_growth → display as "1.8%"
   - Embed the data directly in your JavaScript, don't make it up
   
8. If WEB SEARCH RESULTS are provided:
   - Use for context, citations, and additional information
   - Extract any additional data points from snippets
   - Include source URLs as clickable links
   - Add "Source: [Name]" attributions

9. Create CONTENT-RICH applications:
   - Use real numbers and values provided
   - Create meaningful visualizations from scraped tables
   - **INCLUDE text content, summaries, and analysis from scraped articles**
   - **Don't just show charts - add explanatory text and commentary**
   - Make data interactive and explorable
   - Don't use placeholder data when real data is available
   - If tables exist, create charts/graphs automatically
   - **Add narrative sections with insights from the source material**
   - Include key findings, trends, and context from scraped best_chunk content

TECHNICAL REQUIREMENTS:
10. Use vanilla JavaScript or minimal libraries (Chart.js for charts, Leaflet for maps)
11. Include comprehensive comments
12. Handle errors gracefully
13. Use semantic HTML5
14. Ensure accessibility (ARIA labels, keyboard navigation)
15. For tabular data, create sortable/filterable interactive tables
16. Add download/export functionality for data when appropriate
17. **Include content sections with text from scraped articles, not just visualizations**
18. **Create a balance: visualizations + explanatory text + analysis + commentary**"""

        if is_update:
            return base_rules + "\n\nYou will UPDATE an existing application."
        else:
            return base_rules + "\n\nYou will CREATE a new application."
    
    def save_html_app(self, html_content: str) -> str:
        """Save HTML to file"""
        self.iteration_count += 1
        filename = f"app_{self.iteration_count}.html"
        filepath = Path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath.absolute())
    
    def save_reasoning_logs(self, filename: str = "reasoning_log.json"):
        """Save reasoning logs to JSON"""
        if self.reasoning_logs:
            with open(filename, 'w') as f:
                json.dump(self.reasoning_logs, f, indent=2)
            print(f"\n✅ Reasoning logs saved to {filename}")
            return filename
        return None
    
    def get_scrape_summary(self) -> Dict:
        """Get summary of last scraping operation"""
        if not self.reasoning_logs:
            return {}
        
        scrape_logs = [
            log for log in self.reasoning_logs 
            if log['step'] == 'SCRAPER'
        ]
        
        return {
            'total_scrapes': len(scrape_logs),
            'logs': scrape_logs
        }


# Example usage
def example_usage():
    prompt = "" 

if __name__ == "__main__":
    print("\n⚠️  Configure API keys before running!")
    print("⚠️  This will make multiple API calls and scrape web pages")
    print("⚠️  Estimated cost: ~$0.20-0.80 per generation\n")
    
    asyncio.run(example_usage())