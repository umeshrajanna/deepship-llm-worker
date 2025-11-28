"""
Enhanced Markdown Report Generator with Multi-Stage Research Pipeline + Web Scraping

This generator creates rich Markdown reports with embedded SVG visualizations by:
1. Planning research before building
2. Executing multiple targeted searches
3. Scraping and extracting structured data from URLs using NoirScraper
4. Extracting structured data from results
5. Generating comprehensive Markdown reports with embedded SVG charts/tables
"""

import json
import re
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union, Tuple
# from openai import AsyncOpenAI
import aiohttp
from pathlib import Path

# Import the enhanced transformer
from query_transformer import EnhancedQueryTransformer

# Initialize OpenAI client
import os
from anthropic import AsyncAnthropic
key = os.getenv("LLM_API_KEY")
client = AsyncAnthropic(api_key=key)

# Google Custom Search API credentials
GOOGLE_API_KEY = "AIzaSyDGUJz3wavssYikx5wDq0AcD2QlRt4vS5c"
GOOGLE_CSE_ID = "650310331e0e3490e"
 
# NoirScraper API endpoint
NOIR_SCRAPER_URL = "https://noirscraper-production.up.railway.app/scrape_and_extract"

class WebScraper:
    """Web scraper using NoirScraper API"""
    
    @staticmethod
    async def scrape_urls(
        urls: List[str],
        query: str,
        timeout: int = 30,
        chunk_size: int = 400,
        concurrency: int = 10
    ) -> List[Dict]:
         
        """
        Scrape multiple URLs using NoirScraper API
        
        Args:
            urls: List of URLs to scrape
            query: Search query for relevance scoring
            timeout: Request timeout in seconds
            chunk_size: Size of text chunks for processing (default: 400)
            concurrency: Number of concurrent scraping operations (default: 10)
            
        Returns:
            List of scrape results
        """
        
        payload = {
            "urls": urls,
            "chunk_size": chunk_size,
            "query": query,
            "concurrency": concurrency
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    NOIR_SCRAPER_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    if response.status != 200:
                        # print(f"[SCRAPER] Error: Status {response.status}")
                        # return [{
                        #     'url': url,
                        #     'best_chunk': '',
                        #     'score': 0.0,
                        #     'chunk_index': -1,
                        #     'word_count': 0,
                        #     'total_chunks': 0,
                        #     'tables': [],
                        #     'tables_count': 0,
                        #     'error': f'HTTP {response.status}'
                        # } for url in urls]
                        
                        results = [{
                            'url': url,
                            'best_chunk': '',
                            'score': 0.0,
                            'chunk_index': -1,
                            'word_count': 0,
                            'total_chunks': 0,
                            'tables': [],
                            'tables_count': 0,
                            'error': f'HTTP {response.status}'
                        } for url in urls]
                        yield {"type":"error","content": results}
                        
                    data = await response.json()
                    
                    # Handle NoirScraper's response format
                    if isinstance(data, dict):
                        if not data.get('ok', False):
                            error_msg = data.get('error', 'Unknown error')
                            # print(f"[SCRAPER] API returned error: {error_msg}")
                            # return [{
                            #     'url': url,
                            #     'best_chunk': '',
                            #     'score': 0.0,
                            #     'chunk_index': -1,
                            #     'word_count': 0,
                            #     'total_chunks': 0,
                            #     'tables': [],
                            #     'tables_count': 0,
                            #     'error': error_msg
                            # } for url in urls]
                            
                            results = [{
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
                            
                            yield {"type":"error","content": results}
                        
                        if 'results' in data:
                            results = data['results']
                            if not isinstance(results, list):
                                # print(f"[SCRAPER] Results is not a list")
                                # return [{
                                #     'url': url,
                                #     'best_chunk': '',
                                #     'score': 0.0,
                                #     'chunk_index': -1,
                                #     'word_count': 0,
                                #     'total_chunks': 0,
                                #     'tables': [],
                                #     'tables_count': 0,
                                #     'error': 'Invalid results format'
                                # } for url in urls]                                
                                
                                results = [{
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
                            
                                yield {"type":"error","content": results}
                            
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
                            
                            # return results
                            yield {"type":"scrape_content","content": results}
                        else:
                            print(f"[SCRAPER] No 'results' field in response")
                            # return [{
                            #     'url': url,
                            #     'best_chunk': '',
                            #     'score': 0.0,
                            #     'chunk_index': -1,
                            #     'word_count': 0,
                            #     'total_chunks': 0,
                            #     'tables': [],
                            #     'tables_count': 0,
                            #     'error': 'No results field'
                            # } for url in urls]
                            
                            results = [{
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
                            
                            yield {"type":"error","content": results}
                    
                    elif isinstance(data, list):
                        yield {"type":"scrape_content","content": data}
                        # return data
                    
                    else:
                        print(f"[SCRAPER] Unexpected response format: {type(data)}")
                        # return [{
                        #     'url': url,
                        #     'best_chunk': '',
                        #     'score': 0.0,
                        #     'chunk_index': -1,
                        #     'word_count': 0,
                        #     'total_chunks': 0,
                        #     'tables': [],
                        #     'tables_count': 0,
                        #     'error': 'Invalid response format'
                        # } for url in urls]
                        
                        results = [{
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
                            
                        yield {"type":"error","content": results}
                    
        except asyncio.TimeoutError:
            print(f"[SCRAPER] Timeout after {timeout}s")
            # return [{
            #     'url': url,
            #     'best_chunk': '',
            #     'score': 0.0,
            #     'chunk_index': -1,
            #     'word_count': 0,
            #     'total_chunks': 0,
            #     'tables': [],
            #     'tables_count': 0,
            #     'error': 'Timeout'
            # } for url in urls]
            
            results = [{
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
                
            yield {"type":"error","content": results}
            
        except Exception as e:
            print(f"[SCRAPER] Exception: {e}")
            # return [{
            #     'url': url,
            #     'best_chunk': '',
            #     'score': 0.0,
            #     'chunk_index': -1,
            #     'word_count': 0,
            #     'total_chunks': 0,
            #     'tables': [],
            #     'tables_count': 0,
            #     'error': str(e)
            # } for url in urls]

            results = [{
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
                
            yield {"type":"scrape_content","content": results}

class WebSearcher:
    """Enhanced web searcher with better result handling"""
    
    @staticmethod
    async def search_google(query: str, num_results: int = 10) -> List[Dict]:
        
        # return [
        #     {
        #         "link": "https://weather.metoffice.gov.uk/forecast/gcpvj0v07#?date=2025-11-04",
        #         "snippet": "snippet",
        #         "title": "title"
        #     }]
           
        """
        Perform Google Custom Search
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
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"[SEARCH] Error: Status {response.status}")
                        return []
                        # yield {"type":"google_results","content": []}
                    
                    data = await response.json()
                    
                    results = []
                    for item in data.get('items', []):
                        results.append({
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'snippet': item.get('snippet', '')
                        })
                    
                    return results
                    # yield {"type":"google_results","content": results}
        except Exception as e:
            print(f"[SEARCH] Exception: {e}")
            # yield {"type":"google_results","content": []}
            return []


class DataExtractor:
    """Extracts structured data from search results and scraped content"""
    
    @staticmethod
    async def extract_structured_data(
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        data_types: List[str],
        user_query: str
    ) -> Dict:
        """
        Extract structured data from all search results and scraped content
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
                
                if scrape.get('best_chunk'):
                    scraped_context += f"\nContent (chunk {scrape['chunk_index']}/{scrape['total_chunks']}):\n"
                    scraped_context += scrape['best_chunk'][:2000]
                    scraped_context += "\n"
                
                if scrape.get('tables'):
                    scraped_context += f"\nTables Found: {scrape['tables_count']}\n"
                    for j, table in enumerate(scrape['tables'], 1):
                        scraped_context += f"\nTable {j}:\n"
                        scraped_context += json.dumps(table, indent=2)[:1000]
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

Extract ALL relevant data from both search snippets and scraped content above.
Tables from scraped content should be carefully parsed into structured formats.
Return ONLY valid JSON, no explanations.

Your extracted JSON:"""

        try:
            # response = await asyncio.wait_for(
            #     client.chat.completions.create(
            #         model="gpt-4o",
            #         messages=[{"role": "user", "content": extraction_prompt}],
            #         max_tokens=4000,
            #         temperature=0.3,
            #         timeout=60.0
            #     ),
            #     timeout=90.0
            # )
            
            response = await asyncio.wait_for(
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": extraction_prompt}]
            ),
            timeout=90.0
        )
            
            extracted_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text[7:]
            if extracted_text.startswith("```"):
                extracted_text = extracted_text[3:]
            if extracted_text.endswith("```"):
                extracted_text = extracted_text[:-3]
            extracted_text = extracted_text.strip()
            
            extracted_data = json.loads(extracted_text)
            
            # print(f"[DATA_EXTRACTOR] Successfully extracted structured data")
            # print(f"[DATA_EXTRACTOR] Data keys: {list(extracted_data.keys())}")
            # yield {"type":"structured_data","content": extracted_data}
            return extracted_data
            
        except asyncio.TimeoutError:
            print(f"[DATA_EXTRACTOR] Timeout during extraction (took >90s)")
            print(f"[DATA_EXTRACTOR] Continuing without structured data extraction")
            return {}
            # yield {"type":"structured_data","content": {}}
        except json.JSONDecodeError as e:
            print(f"[DATA_EXTRACTOR] JSON parse error: {e}")
            print(f"[DATA_EXTRACTOR] Response: {extracted_text[:200]}...")
            # yield {"type":"structured_data","content": {}}
            return {}
        except asyncio.CancelledError:
            print(f"[DATA_EXTRACTOR] Extraction cancelled")
            # yield {"type":"structured_data","content": {}}
            return {}
        except Exception as e:
            print(f"[DATA_EXTRACTOR] Error: {e}")
            # yield {"type":"structured_data","content": {}}
            return {}


class EnhancedMarkdownReportGenerator:
    """
    Enhanced Markdown Report Generator with multi-stage research pipeline + web scraping
    Generates rich Markdown reports with embedded SVG visualizations
    """
    async def _generate_html(
        self,
        markdown_content: str
    ) -> str:
        """
        Generate a stunning HTML website from markdown content.
        LLM handles all CSS and styling decisions.
        NO DATA LOSS - uses 100% of markdown content.
        """
        
        # Minimal prompt - let LLM do the heavy lifting
        system_prompt = """You are an expert web developer who creates beautiful, modern, interactive websites.
You convert markdown content into stunning HTML with embedded CSS and JavaScript.
You NEVER lose data - every piece of content must appear in the final HTML."""

        user_prompt = f"""Convert this Markdown into a beautiful, modern HTML website.

MARKDOWN CONTENT:
```markdown
{markdown_content}
```

REQUIREMENTS:

1. **Create a stunning, modern design** with:
   - Beautiful color scheme and gradients
   - Professional typography
   - Smooth animations and transitions
   - Responsive layout

2. **Organize content into 4 tabs**:
   - Overview (summary + key findings)
   - Data Analysis (tables + charts)
   - Detailed Insights (analysis + conclusions)
   - Sources (references)

3. **Preserve ALL content**:
   - Convert ALL markdown tables to HTML tables
   - Include ALL SVG charts exactly as-is
   - Include ALL text, analysis, and commentary
   - No truncation, no placeholders, no data loss

4. **Make it interactive**:
   - Tab navigation with smooth transitions
   - Hover effects on tables and buttons
   - Animated page load
   - Mobile responsive

5. **Self-contained**:
   - Everything in one HTML file
   - CSS in <style> tag
   - JavaScript in <script> tag
   - No external dependencies

Generate the COMPLETE HTML file.
Output ONLY the HTML (no explanations, no markdown code blocks)."""

        # Generate HTML with LLM
        start_time = datetime.now()
        
        # response = await client.chat.completions.create(
        #     model="gpt-5",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_prompt}
        #     ],
        # )
         
        # html_content = response.choices[0].message.content.strip()
        
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        html_content = response.content[0].text.strip()

        # Clean up code blocks if present
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        elif html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()
        
        # Validate HTML
        if not html_content.lower().startswith("<!doctype") and not html_content.lower().startswith("<html"):
            self._log("WARNING", "Generated content doesn't look like HTML, wrapping")
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Report</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        # Store state
        self.current_html = html_content
        
        if self.verbose:
            self._log("HTML", f"Generated {len(html_content)} characters")
        
        yield {"type":"html","content":html_content}
        # return html_content
    
    
    def __init__(
        self, 
        enable_reasoning_capture: bool = False,
        verbose: bool = False,
        max_search_queries: int = 10,
        max_urls_to_scrape: int = 5,
        scrape_timeout: int = 600,
        scrape_chunk_size: int = 400,
        scrape_concurrency: int = 10
    ):
        self.conversation_history: List[Dict] = []
        self.user_queries: List[str] = []
        self.iteration_count: int = 0
        self.current_markdown: Optional[str] = None
        
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
        # ✅ ADD THESE TWO LINES:
        # Callbacks for queue-based architecture  
        self.scraper_callback: Optional[Callable] = None  # Will be injected by LLM worker
        self.progress_callback: Optional[Callable] = None  # Will be injected by LLM worker
    
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
    
    async def develop_report(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict]] = None,
        use_multi_stage: bool = True,
        enable_scraping: bool = True,
        return_conversation: bool = False
    ) -> Union[str, Tuple[str, List[Dict]]]:
        """
        Main entry point - generates Markdown report with optional multi-stage research and scraping
        
        Args:
            user_prompt: User's request
            conversation_history: Previous conversation for context
            use_multi_stage: If True, uses full research pipeline
            enable_scraping: If True, scrapes top URLs for deeper content
            return_conversation: If True, returns (markdown, conversation_history) tuple
        
        Returns:
            If return_conversation=False: Complete Markdown as string
            If return_conversation=True: Tuple of (markdown_string, updated_conversation_history)
        """
        
        self._log("STAGE", f"Starting report development: {user_prompt[:100]}...")
        
        if conversation_history:
            await self._reconstruct_context(conversation_history)
        
        self.user_queries.append(user_prompt)
        analysis_summary = None
        
        # Generate Markdown
        if use_multi_stage:
            yield {"type": "reasoning","content":"Developing with a multi-stage pipeline"}
            
            async for result in self._develop_with_research_pipeline(
                user_prompt,
                enable_scraping=enable_scraping
            ):
                if result.get("type") == "markdown":
                    markdown = result.get("content")
                elif result.get("type") == "analysis_summary":
                    analysis_summary = result.get("content")
                else:
                    yield result
                    
            #     markdown = await self._develop_with_research_pipeline(
            #     user_prompt,
            #     enable_scraping=enable_scraping
            # )
        else:
            markdown = await self._develop_simple(user_prompt)
        
        if return_conversation:
            yield {"type": "reasoning","content":"Developed complete research report..."}            
            yield {"type":"markdown","content":markdown}
            if analysis_summary:
                yield {"type": "analysis_summary", "content": analysis_summary}
            yield {"type":"done","content":""}
            # return markdown, self.get_conversation_history()
        else:
            yield {"type": "reasoning","content":"Developed complete research report..."}    
            yield {"type":"markdown","content":markdown}
            if analysis_summary:
                yield {"type": "analysis_summary", "content": analysis_summary}
            yield {"type":"done","content":"done"}
            # return markdown
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the current conversation history"""
        return self.conversation_history.copy()
    
    async def _reconstruct_context(self, history: List[Dict]):
        """Reconstruct conversation context from history"""
        
        self._log("CONTEXT", f"Reconstructing from {len(history)} messages")
        
        self.user_queries = [
            msg["content"] for msg in history 
            if msg["role"] == "user"
        ]
        
        self.conversation_history = []
        
        if not any(msg.get("role") == "system" for msg in history):
            system_prompt = self._get_system_prompt(is_update=False)
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        for msg in history:
            if msg["role"] == "user":
                self.conversation_history.append(msg)
            elif msg["role"] == "assistant":
                content = msg["content"]
                if content.startswith("#"):
                    self.current_markdown = content
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": "Generated Markdown report with requested features."
                    })
                else:
                    self.conversation_history.append(msg)
        
        self._log("CONTEXT", f"Has existing Markdown: {self.current_markdown is not None}")
        
    def _get_system_prompt(self, is_update: bool) -> str:
        """Get system prompt for generation"""
        
        base_rules = """You are an expert technical writer and data analyst creating comprehensive Markdown reports with embedded SVG visualizations.

    CRITICAL RULES:
    1. Output ONLY complete Markdown - no explanations, no code blocks around the markdown
    2. Create rich, well-formatted Markdown with proper headers, lists, emphasis, and links
    3. Professional, clear, and informative writing style
    4. Include all relevant data and insights from provided sources

    DATA USAGE RULES (MOST IMPORTANT):
    5. If SCRAPED WEB CONTENT is provided:
    - This contains full article text and extracted tables
    - Tables are pre-structured JSON data ready for visualization
    - best_chunk contains the most relevant excerpts from each source
    - Use this data directly - these are real values, not examples
    - Convert ALL tables into embedded SVG visualizations
    
    6. If EXTRACTED STRUCTURED DATA is provided:
    - This is pre-parsed, ready-to-use JSON data
    - Use these EXACT values in your report
    - Example: data.countries["United States"].gdp_growth → "1.8%"
    - Embed the data directly in your visualizations
    
    7. If WEB SEARCH RESULTS are provided:
    - Use for context, citations, and additional information
    - Extract any additional data points from snippets
    - Include source URLs as Markdown links: [Title](URL)
    - Add "Source: [Name]" attributions

    8. Create CONTENT-RICH reports:
    - Use real numbers and values provided
    - Create meaningful SVG visualizations from scraped tables
    - **INCLUDE text content, summaries, and analysis from scraped articles**
    - **Don't just show charts - add explanatory text and commentary**
    - Make data interactive and explorable through well-designed SVGs
    - Don't use placeholder data when real data is available
    - **Add narrative sections with insights from the source material**

    SVG VISUALIZATION REQUIREMENTS:
    9. Convert ALL tabular data into embedded SVG visualizations
    10. Choose appropriate visualization types:
        - Bar charts for categorical comparisons
        - Line charts for time series and trends
        - SVG tables for detailed structured data
        - Pie/donut charts for proportions
    11. SVG Technical Requirements:
        - Use viewBox for responsiveness: viewBox="0 0 [width] [height]"
        - Include proper labels, legends, titles, and axes
        - Use readable fonts (12-16px) and professional colors
        - Add proper spacing and alignment
        - Create clean borders and gridlines where appropriate
        - Ensure text is dark on light backgrounds for readability
    12. Embed SVGs directly in Markdown (no code blocks):
        <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
        <!-- SVG content here -->
        </svg>

    MARKDOWN FORMATTING REQUIREMENTS:
    13. Use proper Markdown syntax:
        - # for main title (only one)
        - ## for major sections
        - ### for subsections
        - **bold** for emphasis
        - *italic* for secondary emphasis
        - [text](url) for all links
        - > for blockquotes
        - - or * for bullet lists
        - 1. 2. 3. for numbered lists
        - --- for horizontal rules between sections
    14. Structure reports logically with clear sections
    15. Include table of contents for longer reports
    16. Add proper spacing between sections
    17. Use blockquotes to highlight key insights or quotes from sources

    CONTENT REQUIREMENTS:
    18. Include an executive summary with key insights
    19. **Add extensive commentary and analysis from scraped article content**
    20. Create narrative descriptions alongside ALL visualizations
    21. **Use the hundreds of words from best_chunk content - this is valuable!**
    22. Include relevant quotes or key points from scraped articles
    23. Add context sections explaining trends, patterns, and implications
    24. Make reports informative and educational, not just visual
    25. **Balance visualizations with explanatory text and analysis**
    26. Include sources section with clickable links at the end

    CRITICAL: When scraped content contains hundreds of words of article text:
    - Don't just extract numbers for charts
    - Include the surrounding analysis, commentary, and insights
    - Create narrative sections that explain what the data means
    - Use direct quotes from sources when relevant
    - Add interpretive text that contextualizes the visualizations

    Example report structure:
    # [Report Title]

    ## Executive Summary
    [2-3 paragraphs synthesizing key insights from all sources]

    ## Key Findings
    - **Finding 1:** [Explanation with data]
    - **Finding 2:** [Explanation with data]

    ## [Topic Area 1]

    ### Overview
    [Narrative explanation from scraped content]

    ### Data Analysis

    <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
    [Chart visualization]
    </svg>

    **Key Insights:**
    - [Insight 1 from data]
    - [Insight 2 from data]

    [Extended analysis and commentary from source material]

    ## [Topic Area 2]
    [Repeat pattern]

    ---

    ## Sources
    1. [Source Title](URL) - [Description]
    2. [Source Title](URL) - [Description]"""

        if is_update:
            return base_rules + "\n\nYou will UPDATE an existing Markdown report based on new requirements."
        else:
            return base_rules + "\n\nYou will CREATE a new comprehensive Markdown report."
    
    async def _generate_research_summary(
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
            
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.7,
                system="You are an expert analyst explaining complex research processes. You articulate how raw data becomes insights through analytical thinking, pattern recognition, and synthesis.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary = response.choices[0].message.content.strip()
            
            return summary
            
        except Exception as e:
            self._log("ERROR", f"Failed to generate analytical summary: {e}")
            return f"Unable to generate analytical summary: {e}"
        
    
    async def _develop_with_research_pipeline(
        self,
        user_prompt: str,
        enable_scraping: bool = True
    ) -> str:
        """Full multi-stage research pipeline with web scraping"""
        
        # STAGE 1: Query Transformation
        transform_result = None
        
        async for result in self.transformer.get_transformed_query(
            user_prompt,
            self.user_queries[:-1]
        ):
            if result.get("type") == "transformed_query":
                yield {"type":"reasoning","content":result.get("content")}
            
            if result.get("type") == "transformer_output":
                transform_result = result.get("content")

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
        
        if not web_search_needed or not search_queries:
            self._log("STAGE", "No research needed, generating directly")
            yield {"type": "reasoning","content":"Developing report..."}
        
            markdown = await self._generate_markdown(user_prompt, {}, [], {})
            yield {"type":"markdown","content":markdown}
            return
        
        # STAGE 2: Execute Web Searches
        all_search_results = {}
        all_urls = []
        search_queries = search_queries[1:]  # Skip first query (usually too broad)
        
        for i, query in enumerate(search_queries, 1):
            self._log("SEARCH", f"[{i}/{len(search_queries)}] {query}")
            
            results = await self.searcher.search_google(query, num_results=10)
            all_search_results[query] = results
            
            currentUrls = []
            for result in results:
                if result['link'] not in all_urls:
                    all_urls.append(result['link'])
                    currentUrls.append(result['link'])
           
            content = {"transformed_query":query,"urls":currentUrls}
            yield {"type":"sources","content":content}
            
            self._log("SEARCH", f"  Found {len(results)} results")
            
            if i < len(search_queries):
                await asyncio.sleep(0.3)  # Rate limiting
                
        yield {"type": "reasoning","content":f"found {len(all_urls)} sources..."}
        scraped_results = []
        
        # STAGE 3: Scrape URLs (Queue-based or Standalone)
        if enable_scraping and all_urls:
            self._log("STAGE", f"=== STAGE 3: Scraping Top {min(len(all_urls), self.max_urls_to_scrape)} URLs ===")
            yield {"type": "reasoning","content":f"performing deep analysis... "}
                
            urls_to_scrape = all_urls[:self.max_urls_to_scrape]
            
            self._log("SCRAPER", f"Scraping {len(urls_to_scrape)} URLs...")
            for url in urls_to_scrape:
                self._log("SCRAPER", f"  - {url}")
            
            primary_query = search_queries[0] if search_queries else user_prompt
            
            # ============================================================================
            # ✅ CRITICAL: CHECK IF CALLBACK IS INJECTED (queue-based) OR USE DIRECT SCRAPER (standalone)
            # ============================================================================
            
            if self.scraper_callback:
                # ====================================================================
                # QUEUE-BASED MODE: Call scraper worker via callback
                # ====================================================================
                print("=" * 80)
                print("[DEEP_SEARCH] Using scraper callback (queue-based mode)")
                print("=" * 80)
                print(f"Calling scraper with {len(urls_to_scrape)} URLs")
                print(f"Primary query: {primary_query}")
                print(f"Original query: {user_prompt}")
                print("=" * 80)
                
                try:
                    # Call the injected callback (LLM worker will send to scraper queue)
                    scraped_results = self.scraper_callback(
                        urls_to_scrape,
                        primary_query,
                        user_prompt  # original_query
                    )
                    
                    print(f"[DEEP_SEARCH] Scraper callback returned: {type(scraped_results)}")
                    
                    if scraped_results:
                        successful_scrapes = [s for s in scraped_results if not s.get('error')]
                        self._log("SCRAPER", f"Successfully scraped {len(successful_scrapes)}/{len(scraped_results)} URLs")
                        
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
                    
            else:
                # ====================================================================
                # STANDALONE MODE: Use direct scraper (original behavior)
                # ====================================================================
                print("=" * 80)
                print("[DEEP_SEARCH] Using direct scraper (standalone mode)")
                print("=" * 80)
                print(f"Calling NoirScraper API with {len(urls_to_scrape)} URLs")
                print("=" * 80)
                
                async for result in self.scraper.scrape_urls(
                    urls_to_scrape,
                    primary_query,
                    timeout=self.scrape_timeout,
                    chunk_size=self.scrape_chunk_size,
                    concurrency=self.scrape_concurrency
                ):
                    if result.get("type") == "scrape_content":
                        scraped_results = result.get("content")
                        
                        successful_scrapes = [s for s in scraped_results if not s.get('error')]
                        self._log("SCRAPER", f"Successfully scraped {len(successful_scrapes)}/{len(scraped_results)} URLs")
                        
                        for scrape in successful_scrapes:
                            self._log("SCRAPER", 
                                f"  {scrape['url'][:60]}... "
                                f"(score: {scrape['score']:.2f}, "
                                f"tables: {scrape['tables_count']}, "
                                f"words: {scrape['word_count']})")
                            
                    if result.get("type") == "error":
                        yield result
        else:
            self._log("STAGE", "=== STAGE 3: Skipping Web Scraping ===")
        
        # STAGE 4: Extract Structured Data
        stage_num = 4 if enable_scraping else 3
        self._log("STAGE", f"=== STAGE {stage_num}: Extracting Structured Data ===")
        
        try:
            yield {"type": "reasoning","content":f"developing assets..."}
            structured_data = await self.extractor.extract_structured_data(
                all_search_results,
                scraped_results,
                data_types,
                user_prompt
            )
        except asyncio.CancelledError:
            self._log("WARNING", "Data extraction cancelled - continuing without structured data")
            structured_data = {}
        except Exception as e:
            self._log("ERROR", f"Data extraction failed: {e}")
            self._log("WARNING", "Continuing without structured data")
            structured_data = {}
        
        # STAGE 5: Generate Markdown Report
        stage_num += 1
        self._log("STAGE", f"=== STAGE {stage_num}: Generating Markdown Report ===")
                
        markdown = await self._generate_markdown(
            user_prompt,
            all_search_results,
            scraped_results,
            structured_data
        )
        
        self._log("COMPLETE", f"Generated {len(markdown)} characters")
        yield {"type":"markdown","content":markdown}
        
        # STAGE 6: Generate Research Analysis Summary
        self._log("STAGE", "=== Generating Research Analysis Summary ===")
        yield {"type": "reasoning", "content": "Analyzing research thought process..."}
        
        analytical_summary = await self._generate_research_summary(
            user_prompt,
            all_search_results,
            scraped_results,
            structured_data,
            markdown
        )
        
        yield {"type": "analysis_summary", "content": analytical_summary}
        
    async def _develop_simple(self, user_prompt: str) -> str:
        """Simple single-stage generation"""
        
        transform_result = await self.transformer.get_transformed_query(
            user_prompt,
            self.user_queries[:-1]
        )
        
        search_results = {}
        scraped_results = []
        structured_data = {}
        
        if transform_result['web_search_needed'] and transform_result['search_query']:
            query = transform_result['search_query']
            results = await self.searcher.search_google(query, num_results=5)
            search_results[query] = results
        
        markdown = await self._generate_markdown(
            user_prompt,
            search_results,
            scraped_results,
            structured_data
        )
        
        yield {"type":"markdown","content":markdown}
        
        # return await self._generate_markdown(
        #     user_prompt,
        #     search_results,
        #     scraped_results,
        #     structured_data
        # )
    
    
#     async def _generate_markdown(
#         self,
#         user_query: str,
#         search_results: Dict[str, List[Dict]],
#         scraped_results: List[Dict],
#         structured_data: Dict
#     ) -> str:
#         """
#         Generate Markdown report with comprehensive context including scraped data
#         """
        
#         is_update = self.current_markdown is not None
        
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
                
#                 if scrape.get('best_chunk'):
#                     scraped_context += f"\nMost Relevant Content:\n"
#                     scraped_context += "```\n"
#                     scraped_context += scrape['best_chunk'][:3000]
#                     if len(scrape['best_chunk']) > 3000:
#                         scraped_context += "\n... (truncated)"
#                     scraped_context += "\n```\n"
                
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
#             structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your report."
        
#         # Get system prompt
#         system_prompt = self._get_system_prompt(is_update)
        
#         # Build user prompt
#         if is_update:
#             user_prompt = f"""Update the following Markdown report based on this request:

# USER REQUEST: {user_query}

# CURRENT MARKDOWN REPORT:
# {self.current_markdown}
# {search_context}
# {scraped_context}
# {structured_context}


# 🚨 CRITICAL ANTI-LAZINESS RULES 🚨
# 1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
# 2. NEVER use placeholders like "... (more data)" or "etc."
# 3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
# 4. If there are 10 data points, create ALL 10 bars/lines/rows - NO SHORTCUTS
# 5. Every SVG must be production-ready and render perfectly
# 6. Create ACTUAL visualizations, not skeleton examples
# 7. If you don't have enough data, use reasonable sample data - but make it COMPLETE

# SVG COMPLETENESS REQUIREMENTS:
# - Temperature charts: Show at least 8-12 hourly data points
# - Bar charts: Include ALL categories mentioned in the data
# - Tables: Include ALL rows of data, not just headers
# - Line charts: Plot the full time series
# - NO ELLIPSIS (...) or "more items" comments allowed

# EXAMPLE OF WHAT NOT TO DO ❌:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <!-- Additional rows omitted for brevity --> ❌ NEVER DO THIS
# </svg>

# EXAMPLE OF WHAT TO DO ✅:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <rect x="10" y="110" width="780" height="30"/>
#   <text>9am - 14°C</text>
#   <rect x="10" y="140" width="780" height="30"/>
#   <text>12pm - 16°C</text>
#   <!-- ... continue for ALL data points -->
# </svg>

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT contains full-depth article content and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values parsed from all sources
# 3. Convert ALL tables from the scraped data into embedded SVG visualizations
# 4. The best_chunk field contains the most relevant text content from each page
# 5. Create a rich, data-driven report with real values, not templates
# 6. Include source citations as Markdown links: [Source Title](URL)
# 7. For tabular data, create SVG charts (bar charts, line charts, tables) embedded directly in the Markdown
# 8. **CRITICAL: Include text summaries and commentary from the scraped content**
# 9. **DO NOT just show tables/charts - include the actual article text and insights**
# 10. **Create narrative sections that explain the data using the scraped text**

# SVG GENERATION RULES:
# - Create clean, professional SVG visualizations for all tabular data
# - Use appropriate chart types: bar charts for comparisons, line charts for trends, tables for detailed data
# - Include axis labels, legends, and titles in SVGs
# - Use readable fonts and colors (dark text on light background)
# - Make SVGs responsive with viewBox attribute
# - Embed SVGs directly in Markdown using XML syntax
# - Example SVG table structure with borders and proper formatting

# CONTENT REQUIREMENTS:
# - Include an executive summary section with key insights from scraped articles
# - Add commentary and analysis text from the sources
# - Create narrative descriptions alongside all visualizations
# - Use the hundreds of words from best_chunk - don't waste them!
# - Include quotes or key points from the scraped content
# - Add context sections that explain what the data means
# - Use proper Markdown formatting: headers, lists, emphasis, links

# EXAMPLE STRUCTURE:
# # Report Title

# ## Executive Summary
# [Synthesized insights from scraped content]

# ## Key Findings
# [From article text and analysis]

# ## Data Visualizations
# [Embedded SVG charts with explanatory text]

# ### Chart 1: [Title]
# [SVG embedded here]
# [Explanation from scraped content]

# ## Detailed Analysis
# [From best_chunk content with commentary]

# ## Additional Context
# [Trends, patterns, explanations from articles]

# ## Sources & References
# - [Source 1 Title](URL)
# - [Source 2 Title](URL)

# Generate the COMPLETE updated Markdown report (output ONLY the Markdown):"""
#         else:
#             user_prompt = f"""Create a comprehensive Markdown report based on this request:

# USER REQUEST: {user_query}
# {search_context}
# {scraped_context}
# {structured_context}

# 1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
# 2. NEVER use placeholders like "... (more data)" or "etc."
# 3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
# 4. If there are 10 data points, create ALL 10 bars/lines/rows - NO SHORTCUTS
# 5. Every SVG must be production-ready and render perfectly
# 6. Create ACTUAL visualizations, not skeleton examples
# 7. If you don't have enough data, use reasonable sample data - but make it COMPLETE

# SVG COMPLETENESS REQUIREMENTS:
# - Temperature charts: Show at least 8-12 hourly data points
# - Bar charts: Include ALL categories mentioned in the data
# - Tables: Include ALL rows of data, not just headers
# - Line charts: Plot the full time series
# - NO ELLIPSIS (...) or "more items" comments allowed

# EXAMPLE OF WHAT NOT TO DO ❌:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <!-- Additional rows omitted for brevity --> ❌ NEVER DO THIS
# </svg>

# EXAMPLE OF WHAT TO DO ✅:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <rect x="10" y="110" width="780" height="30"/>
#   <text>9am - 14°C</text>
#   <rect x="10" y="140" width="780" height="30"/>
#   <text>12pm - 16°C</text>
#   <!-- ... continue for ALL data points -->
# </svg>

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT provides full-depth article text and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values from all sources
# 3. Convert ALL tables into embedded SVG visualizations (charts, graphs, formatted tables)
# 4. The best_chunk field contains the most relevant excerpts from each source
# 5. Create comprehensive, data-rich visualizations using the provided data
# 6. Include source attribution as Markdown links: [Title](URL)
# 7. Use actual data values, not placeholder or dummy data
# 8. **CRITICAL: Include text summaries, commentary, and analysis from scraped content**
# 9. **DO NOT just show tables/charts - include the article text and insights**
# 10. **Create narrative sections that explain and contextualize the data**

# SVG GENERATION RULES:
# - Create professional SVG visualizations for ALL tabular data from scraped content
# - Choose appropriate chart types:
#   * Bar charts for categorical comparisons
#   * Line charts for time series and trends
#   * Formatted SVG tables for detailed structured data
#   * Pie charts for proportions/percentages
# - Include proper labels, legends, titles, and axes in all SVGs
# - Use clean typography and color schemes (professional color palette)
# - Make SVGs self-contained and responsive (use viewBox)
# - Embed SVGs directly in Markdown using proper XML syntax
# - For tables: create clean SVG tables with borders, headers, and aligned columns

# SVG TABLE EXAMPLE:
# ```svg
# <svg viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg">
#   <rect x="0" y="0" width="600" height="300" fill="white" stroke="black"/>
#   <text x="300" y="30" text-anchor="middle" font-size="16" font-weight="bold">Table Title</text>
#   <!-- Headers -->
#   <rect x="10" y="50" width="580" height="30" fill="#f0f0f0" stroke="black"/>
#   <text x="100" y="70" font-size="14">Column 1</text>
#   <text x="300" y="70" font-size="14">Column 2</text>
#   <!-- Data rows -->
#   <rect x="10" y="80" width="580" height="30" fill="white" stroke="black"/>
#   <text x="100" y="100" font-size="12">Data 1</text>
#   <text x="300" y="100" font-size="12">Data 2</text>
# </svg>
# ```

# SVG BAR CHART EXAMPLE:
# ```svg
# <svg viewBox="0 0 500 300" xmlns="http://www.w3.org/2000/svg">
#   <text x="250" y="20" text-anchor="middle" font-size="16" font-weight="bold">Chart Title</text>
#   <!-- Bars -->
#   <rect x="50" y="250" width="80" height="100" fill="#4CAF50"/>
#   <text x="90" y="270" text-anchor="middle" font-size="12">Label</text>
#   <!-- Y-axis labels -->
#   <text x="30" y="150" font-size="10">50</text>
# </svg>
# ```

# CONTENT REQUIREMENTS:
# - Include an executive summary section with key insights from scraped articles
# - Add commentary and analysis text from the sources
# - Create narrative descriptions alongside ALL visualizations
# - Use the hundreds of words from best_chunk content - this is valuable information!
# - Include relevant quotes, key points, or highlights from scraped articles
# - Add context sections that explain trends, patterns, or what the data means
# - Use proper Markdown formatting throughout: headers, bold, italic, lists, links
# - Make the report informative and educational, not just visual

# MARKDOWN FORMATTING:
# - Use # for main title, ## for sections, ### for subsections
# - Use **bold** for emphasis, *italic* for secondary emphasis
# - Create bulleted lists with - or *
# - Create numbered lists with 1., 2., 3.
# - Add horizontal rules with --- for section breaks
# - Use > for blockquotes when citing key excerpts
# - Use [text](url) for all source links

# EXAMPLE STRUCTURE:
# # [Report Title]

# ## Executive Summary
# [Synthesized from scraped article content - 2-3 paragraphs of key insights]

# ## Key Findings & Insights
# [From article text and analysis - bullet points with explanations]

# ### Finding 1: [Title]
# [Explanation from scraped content]

# ### Finding 2: [Title]
# [Explanation from scraped content]

# ## Data Visualizations

# ### [Visualization 1 Title]

# [Embedded SVG chart/table here]

# **Analysis:** [Detailed explanation using scraped content - what does this data show? Why is it important?]

# ### [Visualization 2 Title]

# [Embedded SVG chart/table here]

# **Analysis:** [Explanation from sources]

# ## Detailed Analysis
# [Deep dive using best_chunk content with full commentary and context]

# ### [Topic 1]
# [Rich text content from scraped articles with analysis]

# ### [Topic 2]
# [Rich text content from scraped articles with analysis]

# ## Additional Context
# [Trends, patterns, implications, and explanations from articles]

# ## Conclusions
# [Summary of key takeaways]

# ---

# ## Sources & References
# 1. [Source 1 Title](URL) - [Brief description]
# 2. [Source 2 Title](URL) - [Brief description]

# The scraped content contains hundreds of words of valuable information - USE IT ALL!
# Don't just extract numbers for charts - include the surrounding analysis and commentary.
# Create a balanced report: visualizations + explanatory text + analysis + commentary.

# Generate the COMPLETE Markdown report (output ONLY the Markdown):"""

# # Add to conversation history
#         if not self.conversation_history:
#             self.conversation_history.append({
#                 "role": "system",
#             "content": system_prompt
#             })
        
#         self.conversation_history.append({
#             "role": "user",
#             "content": user_prompt
#         })
        
#         # Generate with GPT-4o (THIS IS THE MISSING PART!)
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
        
#         markdown_content = response.choices[0].message.content.strip()
        
#         # Clean up markdown code blocks
#         if markdown_content.startswith("```markdown"):
#             markdown_content = markdown_content[11:]
#         elif markdown_content.startswith("```md"):
#             markdown_content = markdown_content[5:]
#         elif markdown_content.startswith("```"):
#             markdown_content = markdown_content[3:]
#         if markdown_content.endswith("```"):
#             markdown_content = markdown_content[:-3]
#         markdown_content = markdown_content.strip()
        
#         # Validate it's markdown
#         if not markdown_content.startswith("#") and "##" not in markdown_content[:500]:
#             self._log("WARNING", "Generated content doesn't look like Markdown, wrapping with header")
#             markdown_content = f"# Generated Report\n\n{markdown_content}"
        
#         # Store state
#         self.current_markdown = markdown_content
        
#         # Add summary to conversation
#         summary = f"Generated Markdown report with requested features."
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
        
#         return markdown_content
    
#     async def _generate_markdown(
#         self,
#         user_query: str,
#         search_results: Dict[str, List[Dict]],
#         scraped_results: List[Dict],
#         structured_data: Dict
#     ) -> str:
#         """
#         Generate Markdown report with comprehensive context including scraped data
#         """
        
#         is_update = self.current_markdown is not None
        
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
                
#                 if scrape.get('best_chunk'):
#                     scraped_context += f"\nMost Relevant Content:\n"
#                     scraped_context += "```\n"
#                     scraped_context += scrape['best_chunk'][:3000]
#                     if len(scrape['best_chunk']) > 3000:
#                         scraped_context += "\n... (truncated)"
#                     scraped_context += "\n```\n"
                
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
#             structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your report."
        
#         # Get system prompt
#         system_prompt = self._get_system_prompt(is_update)
        
#         # Build user prompt
#         if is_update:
#             user_prompt = f"""Update the following Markdown report based on this request:

# USER REQUEST: {user_query}

# CURRENT MARKDOWN REPORT:
# {self.current_markdown}
# {search_context}
# {scraped_context}
# {structured_context}


# 🚨 CRITICAL ANTI-LAZINESS RULES 🚨
# 1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
# 2. NEVER use placeholders like "... (more data)" or "etc."
# 3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
# 4. If there are 10 data points, create ALL 10 bars/lines/rows - NO SHORTCUTS
# 5. Every SVG must be production-ready and render perfectly
# 6. Create ACTUAL visualizations, not skeleton examples
# 7. If you don't have enough data, use reasonable sample data - but make it COMPLETE

# SVG COMPLETENESS REQUIREMENTS:
# - Temperature charts: Show at least 8-12 hourly data points
# - Bar charts: Include ALL categories mentioned in the data
# - Tables: Include ALL rows of data, not just headers
# - Line charts: Plot the full time series
# - NO ELLIPSIS (...) or "more items" comments allowed

# EXAMPLE OF WHAT NOT TO DO ❌:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <!-- Additional rows omitted for brevity --> ❌ NEVER DO THIS
# </svg>

# EXAMPLE OF WHAT TO DO ✅:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <rect x="10" y="110" width="780" height="30"/>
#   <text>9am - 14°C</text>
#   <rect x="10" y="140" width="780" height="30"/>
#   <text>12pm - 16°C</text>
#   <!-- ... continue for ALL data points -->
# </svg>

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT contains full-depth article content and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values parsed from all sources
# 3. **MANDATORY: For EVERY table in the data, you MUST create BOTH:**
#    a) A properly formatted Markdown table with ALL rows and columns
#    b) An SVG visualization (chart/graph) representing the same data
# 4. The best_chunk field contains the most relevant text content from each page
# 5. Create a rich, data-driven report with real values, not templates
# 6. Include source citations as Markdown links: [Source Title](URL)
# 7. **DOUBLE REPRESENTATION REQUIREMENT**: Every piece of tabular data must appear as:
#    - A complete Markdown table (for detailed reference)
#    - An SVG chart (for visual understanding)
# 8. **CRITICAL: Include text summaries and commentary from the scraped content**
# 9. **DO NOT just show tables/charts - include the actual article text and insights**
# 10. **Create narrative sections that explain the data using the scraped text**

# MARKDOWN TABLE REQUIREMENTS:
# - Use proper Markdown table syntax with | separators
# - Include header row with alignment (e.g., | --- | --- |)
# - Include ALL data rows - no truncation or "..." 
# - Ensure proper column alignment
# - Add table caption before each table

# EXAMPLE MARKDOWN TABLE:
# **Table 1: Sample Data**

# | Column 1 | Column 2 | Column 3 |
# |----------|----------|----------|
# | Data 1   | Data 2   | Data 3   |
# | Data 4   | Data 5   | Data 6   |
# | Data 7   | Data 8   | Data 9   |

# (Continue for ALL rows)

# SVG GENERATION RULES:
# - Create clean, professional SVG visualizations for all tabular data
# - Use appropriate chart types: bar charts for comparisons, line charts for trends
# - For complex tables, create SVG formatted tables with proper styling
# - Include axis labels, legends, and titles in SVGs
# - Use readable fonts and colors (dark text on light background)
# - Make SVGs responsive with viewBox attribute
# - Embed SVGs directly in Markdown using XML syntax

# VISUALIZATION PAIRING:
# For each dataset, present in this order:
# 1. **Markdown Table** (complete data in tabular format)
# 2. **SVG Chart** (visual representation of the same data)
# 3. **Analysis** (text commentary explaining the data)

# CONTENT REQUIREMENTS:
# - Include an executive summary section with key insights from scraped articles
# - Add commentary and analysis text from the sources
# - Create narrative descriptions alongside all visualizations
# - Use the hundreds of words from best_chunk - don't waste them!
# - Include quotes or key points from the scraped content
# - Add context sections that explain what the data means
# - Use proper Markdown formatting: headers, lists, emphasis, links

# EXAMPLE STRUCTURE:
# # Report Title

# ## Executive Summary
# [Synthesized insights from scraped content]

# ## Key Findings
# [From article text and analysis]

# ## Data Visualizations

# ### Dataset 1: [Title]

# **Table 1: [Descriptive Caption]**

# | Column A | Column B | Column C |
# |----------|----------|----------|
# | Value 1  | Value 2  | Value 3  |
# | Value 4  | Value 5  | Value 6  |
# [... ALL rows ...]

# **Chart 1: [Same Dataset Visualized]**

# <svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
#   <!-- Complete SVG chart here -->
# </svg>

# **Analysis:** [Detailed explanation using scraped content]

# ### Dataset 2: [Title]

# [Repeat: Table → Chart → Analysis]

# ## Detailed Analysis
# [From best_chunk content with commentary]

# ## Additional Context
# [Trends, patterns, explanations from articles]

# ## Sources & References
# - [Source 1 Title](URL)
# - [Source 2 Title](URL)

# Generate the COMPLETE updated Markdown report (output ONLY the Markdown):"""
#         else:
#             user_prompt = f"""Create a comprehensive Markdown report based on this request:

# USER REQUEST: {user_query}
# {search_context}
# {scraped_context}
# {structured_context}

# 🚨 CRITICAL ANTI-LAZINESS RULES 🚨
# 1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
# 2. NEVER use placeholders like "... (more data)" or "etc."
# 3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
# 4. If there are 10 data points, create ALL 10 bars/lines/rows - NO SHORTCUTS
# 5. Every SVG must be production-ready and render perfectly
# 6. Create ACTUAL visualizations, not skeleton examples
# 7. If you don't have enough data, use reasonable sample data - but make it COMPLETE

# SVG COMPLETENESS REQUIREMENTS:
# - Temperature charts: Show at least 8-12 hourly data points
# - Bar charts: Include ALL categories mentioned in the data
# - Tables: Include ALL rows of data, not just headers
# - Line charts: Plot the full time series
# - NO ELLIPSIS (...) or "more items" comments allowed

# EXAMPLE OF WHAT NOT TO DO ❌:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <!-- Additional rows omitted for brevity --> ❌ NEVER DO THIS
# </svg>

# EXAMPLE OF WHAT TO DO ✅:
# <svg>
#   <rect x="10" y="80" width="780" height="30"/>
#   <text>6am - 12°C</text>
#   <rect x="10" y="110" width="780" height="30"/>
#   <text>9am - 14°C</text>
#   <rect x="10" y="140" width="780" height="30"/>
#   <text>12pm - 16°C</text>
#   <!-- ... continue for ALL data points -->
# </svg>

# CRITICAL INSTRUCTIONS FOR DATA USAGE:
# 1. The SCRAPED WEB CONTENT provides full-depth article text and extracted tables
# 2. The EXTRACTED STRUCTURED DATA contains ready-to-use values from all sources
# 3. **MANDATORY: For EVERY table/dataset, you MUST create BOTH:**
#    a) A properly formatted Markdown table with ALL rows and columns
#    b) An SVG visualization (chart/graph) representing the same data
# 4. The best_chunk field contains the most relevant excerpts from each source
# 5. Create comprehensive, data-rich visualizations using the provided data
# 6. Include source attribution as Markdown links: [Title](URL)
# 7. Use actual data values, not placeholder or dummy data
# 8. **DOUBLE REPRESENTATION REQUIREMENT**: Every piece of tabular data must appear as:
#    - A complete Markdown table (for detailed reference and data lookup)
#    - An SVG chart (for visual understanding and pattern recognition)
# 9. **CRITICAL: Include text summaries, commentary, and analysis from scraped content**
# 10. **DO NOT just show tables/charts - include the article text and insights**
# 11. **Create narrative sections that explain and contextualize the data**

# MARKDOWN TABLE REQUIREMENTS:
# - Use proper Markdown table syntax: | Column | Column | Column |
# - Include header separator: |--------|--------|--------|
# - Include ALL data rows without truncation
# - Ensure consistent column widths and alignment
# - Add descriptive captions above each table
# - Use left alignment for text, right for numbers
# - Never use "..." or "etc." in tables

# EXAMPLE MARKDOWN TABLE FORMAT:

# **Table 1: Hourly Temperature Data**

# | Time  | Temperature (°C) | Conditions | Wind Speed (mph) |
# |-------|------------------|------------|------------------|
# | 6am   | 12               | Misty      | 5                |
# | 9am   | 14               | Cloudy     | 6                |
# | 12pm  | 16               | Sunny      | 7                |
# | 3pm   | 15               | Sunny      | 7                |
# | 6pm   | 13               | Clear      | 6                |
# | 9pm   | 11               | Clear      | 3                |

# (Include ALL rows - no shortcuts!)

# SVG GENERATION RULES:
# - Create professional SVG visualizations for ALL tabular data from scraped content
# - Choose appropriate chart types:
#   * Bar charts for categorical comparisons
#   * Line charts for time series and trends
#   * Formatted SVG tables for detailed structured data
#   * Pie charts for proportions/percentages
# - Include proper labels, legends, titles, and axes in all SVGs
# - Use clean typography and color schemes (professional color palette)
# - Make SVGs self-contained and responsive (use viewBox)
# - Embed SVGs directly in Markdown using proper XML syntax

# SVG BAR CHART EXAMPLE:
# <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
#   <text x="300" y="30" text-anchor="middle" font-size="18" font-weight="bold">Chart Title</text>
#   <!-- X and Y axes -->
#   <line x1="50" y1="350" x2="550" y2="350" stroke="black" stroke-width="2"/>
#   <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
#   <!-- Bars -->
#   <rect x="100" y="200" width="60" height="150" fill="#4CAF50"/>
#   <text x="130" y="370" text-anchor="middle" font-size="12">Label 1</text>
#   <rect x="200" y="150" width="60" height="200" fill="#2196F3"/>
#   <text x="230" y="370" text-anchor="middle" font-size="12">Label 2</text>
#   <!-- Y-axis labels -->
#   <text x="40" y="355" text-anchor="end" font-size="10">0</text>
#   <text x="40" y="255" text-anchor="end" font-size="10">50</text>
#   <text x="40" y="155" text-anchor="end" font-size="10">100</text>
# </svg>

# SVG LINE CHART EXAMPLE:
# <svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
#   <text x="400" y="30" text-anchor="middle" font-size="18" font-weight="bold">Temperature Throughout Day</text>
#   <!-- Axes -->
#   <line x1="50" y1="350" x2="750" y2="350" stroke="black" stroke-width="2"/>
#   <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
#   <!-- Line plot -->
#   <polyline points="50,290 150,270 250,250 350,240 450,250 550,270 650,290" 
#             fill="none" stroke="#FF5722" stroke-width="3"/>
#   <!-- Data points -->
#   <circle cx="50" cy="290" r="5" fill="#FF5722"/>
#   <circle cx="150" cy="270" r="5" fill="#FF5722"/>
#   <!-- Labels -->
#   <text x="50" y="370" text-anchor="middle" font-size="10">6am</text>
#   <text x="150" y="370" text-anchor="middle" font-size="10">9am</text>
# </svg>

# VISUALIZATION PAIRING REQUIREMENT:
# For EVERY dataset, present in this specific order:
# 1. **Section Header** (### Title)
# 2. **Markdown Table** (complete data table with all rows)
# 3. **SVG Chart** (visual representation of the same data)
# 4. **Analysis Text** (commentary explaining patterns, insights)

# CONTENT REQUIREMENTS:
# - Include an executive summary section with key insights from scraped articles
# - Add commentary and analysis text from the sources
# - Create narrative descriptions alongside ALL visualizations
# - Use the hundreds of words from best_chunk content - this is valuable information!
# - Include relevant quotes, key points, or highlights from scraped articles
# - Add context sections that explain trends, patterns, or what the data means
# - Use proper Markdown formatting throughout: headers, bold, italic, lists, links
# - Make the report informative and educational, not just visual

# MARKDOWN FORMATTING:
# - Use # for main title, ## for sections, ### for subsections
# - Use **bold** for emphasis, *italic* for secondary emphasis
# - Create bulleted lists with - or *
# - Create numbered lists with 1., 2., 3.
# - Add horizontal rules with --- for section breaks
# - Use > for blockquotes when citing key excerpts
# - Use [text](url) for all source links

# EXAMPLE STRUCTURE:
# # [Report Title]

# ## Executive Summary
# [Synthesized from scraped article content - 2-3 paragraphs of key insights]

# ## Key Findings & Insights
# [From article text and analysis - bullet points with explanations]

# ### Finding 1: [Title]
# [Explanation from scraped content]

# ### Finding 2: [Title]
# [Explanation from scraped content]

# ## Data Visualizations

# ### Dataset 1: [Title]

# **Table 1: [Descriptive Caption]**

# | Column A | Column B | Column C |
# |----------|----------|----------|
# | Data 1   | Data 2   | Data 3   |
# | Data 4   | Data 5   | Data 6   |
# | Data 7   | Data 8   | Data 9   |
# [Include ALL rows]

# **Chart 1: [Same Title - Visual Representation]**

# <svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
#   <!-- Complete SVG chart representing the table data above -->
# </svg>

# **Analysis:** [Detailed explanation using scraped content - what does this data show? Why is it important? What patterns exist?]

# ### Dataset 2: [Title]

# **Table 2: [Caption]**
# [Complete Markdown table]

# **Chart 2: [Visual]**
# [Complete SVG chart]

# **Analysis:** [Explanation from sources]

# ## Detailed Analysis
# [Deep dive using best_chunk content with full commentary and context]

# ### [Topic 1]
# [Rich text content from scraped articles with analysis]

# ### [Topic 2]
# [Rich text content from scraped articles with analysis]

# ## Additional Context
# [Trends, patterns, implications, and explanations from articles]

# ## Conclusions
# [Summary of key takeaways]

# ---

# ## Sources & References
# 1. [Source 1 Title](URL) - [Brief description]
# 2. [Source 2 Title](URL) - [Brief description]

# REMEMBER:
# - The scraped content contains hundreds of words of valuable information - USE IT ALL!
# - Don't just extract numbers for charts - include the surrounding analysis and commentary
# - Create a balanced report: Markdown tables + SVG charts + explanatory text + analysis
# - Every table gets BOTH a Markdown table AND an SVG visualization
# - NO truncation, NO shortcuts, NO placeholders

# Generate the COMPLETE Markdown report (output ONLY the Markdown):"""

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
        
#         # Generate with GPT-4o (THIS IS THE MISSING PART!)
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
        
#         markdown_content = response.choices[0].message.content.strip()
        
#         # Clean up markdown code blocks
#         if markdown_content.startswith("```markdown"):
#             markdown_content = markdown_content[11:]
#         elif markdown_content.startswith("```md"):
#             markdown_content = markdown_content[5:]
#         elif markdown_content.startswith("```"):
#             markdown_content = markdown_content[3:]
#         if markdown_content.endswith("```"):
#             markdown_content = markdown_content[:-3]
#         markdown_content = markdown_content.strip()
        
#         # Validate it's markdown
#         if not markdown_content.startswith("#") and "##" not in markdown_content[:500]:
#             self._log("WARNING", "Generated content doesn't look like Markdown, wrapping with header")
#             markdown_content = f"# Generated Report\n\n{markdown_content}"
        
#         # Store state
#         self.current_markdown = markdown_content
        
#         # Add summary to conversation
#         summary = f"Generated Markdown report with requested features."
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
        
#         return markdown_content
    async def _generate_markdown_with_svg(
        self,
        user_query: str,
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        structured_data: Dict
    ) -> str:
        """
        Generate Markdown report with comprehensive context including scraped data
        """
        
        is_update = self.current_markdown is not None
        
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
                scraped_context += f"**CRITICAL: {scrape.get('tables_count', 0)} TABLES FOUND - YOU MUST ANALYZE AND VISUALIZE EACH ONE**\n"
                
                if scrape.get('best_chunk'):
                    scraped_context += f"\nMost Relevant Content:\n"
                    scraped_context += "```\n"
                    scraped_context += scrape['best_chunk'][:3000]
                    if len(scrape['best_chunk']) > 3000:
                        scraped_context += "\n... (truncated)"
                    scraped_context += "\n```\n"
                
                if scrape.get('tables') and scrape['tables_count'] > 0:
                    scraped_context += f"\n🚨 EXTRACTED TABLES ({scrape['tables_count']} total) - MANDATORY TO PROCESS ALL 🚨\n"
                    for j, table in enumerate(scrape['tables'], 1):
                        scraped_context += f"\n⚠️ TABLE {j} (MUST BE INCLUDED IN REPORT):\n"
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
            structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your report."
        
        # Get system prompt
        system_prompt = self._get_system_prompt(is_update)
        
        # Build user prompt
        if is_update:
            user_prompt = f"""Update the following Markdown report based on this request:

USER REQUEST: {user_query}

CURRENT MARKDOWN REPORT:
{self.current_markdown}
{search_context}
{scraped_context}
{structured_context}

🔥 MANDATORY DATA UTILIZATION REQUIREMENTS 🔥

YOU HAVE RECEIVED {len([s.get('tables', []) for s in scraped_results])} TABLES OF DATA.
YOU MUST CREATE VISUALIZATIONS FOR **AT LEAST 5-10 DIFFERENT DATASETS** FROM THIS DATA.

CRITICAL INSTRUCTIONS:

1. **ANALYZE ALL TABLES**: Examine every table provided. Don't just use the first one!
2. **CREATE MULTIPLE CHART TYPES**: 
   - Temperature line charts
   - Wind speed bar charts
   - Humidity trend charts
   - Precipitation probability charts
   - Comparative charts (feels like vs actual temp)
   - Multi-day comparison charts
   - Visibility charts
   - UV index charts
   - Wind gust comparisons
   - Any other relevant metrics you find in the tables

3. **MANDATORY CHART MINIMUM**: You MUST create AT LEAST 5-8 DIFFERENT SVG CHARTS, each showing different data

4. **DATA EXPLORATION**: Look for:
   - Time series data (hourly, daily trends)
   - Comparative data (multiple days, multiple metrics)
   - Categorical data (weather symbols, visibility levels)
   - Correlations (temperature vs humidity, wind speed vs gusts)

5. **EVERY DATASET NEEDS**:
   a) A complete Markdown table with ALL rows
   b) An SVG visualization (chart/graph)
   c) Analysis explaining the patterns

6. **CHART VARIETY REQUIREMENT**: Use different chart types:
   - Line charts for trends over time
   - Bar charts for comparisons
   - Combo charts showing multiple metrics
   - Color-coded visualization for weather conditions

🚨 CRITICAL ANTI-LAZINESS RULES 🚨
1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
2. NEVER use placeholders like "... (more data)" or "etc."
3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
4. If there are 10 data points, create ALL 10 bars/lines/rows - NO SHORTCUTS
5. Every SVG must be production-ready and render perfectly
6. Create ACTUAL visualizations, not skeleton examples

COMPREHENSIVE REPORT STRUCTURE:

# [Title]

## Executive Summary
[2-3 paragraphs of insights from ALL the data]

## Key Findings
[Major insights derived from analyzing multiple datasets]

## Hourly Forecast Breakdown

### Temperature Analysis
**Table 1: Hourly Temperature Data**
[Complete markdown table with ALL hourly data]

**Chart 1: Temperature Progression**
[SVG line chart showing temperature throughout the day]

**Analysis:** [Explain the temperature patterns]

### Wind Conditions
**Table 2: Wind Speed and Direction**
[Complete markdown table with ALL wind data]

**Chart 2: Wind Speed Variations**
[SVG bar/line chart showing wind patterns]

**Analysis:** [Explain wind patterns]

### Humidity Trends
**Table 3: Humidity Levels**
[Complete markdown table]

**Chart 3: Humidity Throughout Day**
[SVG chart]

**Analysis:** [Explain humidity patterns]

### Precipitation Analysis
**Table 4: Precipitation Probability**
[Complete markdown table]

**Chart 4: Rain Chances**
[SVG chart]

**Analysis:** [Explain precipitation chances]

### Additional Metrics
[Continue with more tables and charts for:]
- UV Index
- Visibility
- Feels Like Temperature
- Wind Gusts
- Weather Symbols/Conditions

## Multi-Day Comparison
**Table X: Multi-Day Forecast**
[Table comparing multiple days if data available]

**Chart X: Multi-Day Trends**
[SVG showing trends across days]

## Detailed Analysis
[Deep insights from the data]

## Conclusions

---

## Sources & References

MINIMUM REQUIREMENTS:
- 5-8 different SVG charts minimum
- Each chart must show different data
- Every chart needs a corresponding markdown table
- Use ALL the table data provided, not just 1-2 tables
- Create comprehensive visualizations showing patterns, trends, comparisons

Generate the COMPLETE updated Markdown report (output ONLY the Markdown):"""
        else:
            user_prompt = f"""Create a comprehensive Markdown report based on this request:

USER REQUEST: {user_query}
{search_context}
{scraped_context}
{structured_context}

🔥 MANDATORY DATA UTILIZATION REQUIREMENTS 🔥

YOU HAVE RECEIVED EXTENSIVE TABULAR DATA WITH MULTIPLE TABLES.
YOU MUST CREATE VISUALIZATIONS FOR **AT LEAST 5-10 DIFFERENT DATASETS** FROM THIS DATA.

CRITICAL INSTRUCTIONS FOR COMPREHENSIVE ANALYSIS:

1. **ANALYZE ALL TABLES PROVIDED**: Don't just use the first table - examine ALL tables in the scraped data
2. **IDENTIFY DIFFERENT DATASETS**: Look for:
   - Hourly temperature data
   - Wind speed and direction
   - Humidity levels
   - Precipitation chances
   - UV index
   - Visibility data
   - Feels like temperature
   - Wind gusts
   - Weather conditions/symbols
   - Multi-day forecasts
   - Comparative data across time periods

3. **MANDATORY: CREATE MULTIPLE VISUALIZATIONS**
   You MUST create AT LEAST 5-8 DIFFERENT charts, including:
   - Temperature line chart (hourly progression)
   - Wind speed bar/line chart
   - Humidity trend chart
   - Precipitation probability chart
   - Temperature comparison (actual vs feels like)
   - Wind gust comparison chart
   - UV index chart
   - Visibility chart
   - Multi-metric comparison chart
   - Any additional charts from available data

4. **CHART TYPE VARIETY**: Use appropriate visualization types:
   - **Line charts**: For time-series data (temperature over time, humidity trends)
   - **Bar charts**: For categorical comparisons (wind speed by hour, precipitation by day)
   - **Multi-line charts**: For comparing multiple metrics (actual temp vs feels like)
   - **Stacked visualizations**: For showing relationships

5. **EVERY DATASET REQUIRES**:
   a) A descriptive section header
   b) A complete Markdown table with ALL rows and columns
   c) An SVG chart visualizing the data
   d) Analysis text explaining patterns and insights

6. **DATA DEPTH REQUIREMENT**: 
   - If you have 18 hours of data, show ALL 18 hours
   - If you have 24 hours, show ALL 24 hours
   - If you have multiple days, show ALL days
   - NO truncation, NO shortcuts

🚨 CRITICAL ANTI-LAZINESS RULES 🚨
1. NEVER use comments like "<!-- Additional rows omitted for brevity -->"
2. NEVER use placeholders like "... (more data)" or "etc."
3. ALWAYS generate COMPLETE, FULLY FUNCTIONAL SVG charts with ALL data points
4. If there are 18 data points, create ALL 18 bars/lines/rows - NO SHORTCUTS
5. Every SVG must be production-ready and render perfectly
6. Create ACTUAL visualizations, not skeleton examples
7. Process EVERY table provided - not just one or two

MARKDOWN TABLE FORMAT:
```
**Table X: [Descriptive Title]**

| Column 1 | Column 2 | Column 3 | Column 4 |
|----------|----------|----------|----------|
| Data 1   | Data 2   | Data 3   | Data 4   |
| Data 5   | Data 6   | Data 7   | Data 8   |
[... ALL rows, no truncation ...]
```

SVG CHART EXAMPLES:

**Line Chart for Time Series:**
```svg
<svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
  <text x="400" y="30" text-anchor="middle" font-size="18" font-weight="bold">Hourly Temperature</text>
  <line x1="50" y1="350" x2="750" y2="350" stroke="black" stroke-width="2"/>
  <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
  <polyline points="50,290 90,285 130,280 170,270 210,265 250,260 290,255 330,260 370,270 410,280 450,290 490,295 530,300 570,305 610,310 650,312 690,315 730,318" 
            fill="none" stroke="#FF5722" stroke-width="3"/>
  <!-- Include circles for ALL data points -->
  <!-- Include labels for ALL time points -->
  <!-- Include Y-axis temperature labels -->
</svg>
```

**Bar Chart for Comparisons:**
```svg
<svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
  <text x="400" y="30" text-anchor="middle" font-size="18" font-weight="bold">Wind Speed by Hour</text>
  <line x1="50" y1="350" x2="750" y2="350" stroke="black" stroke-width="2"/>
  <line x1="50" y1="50" x2="50" y2="350" stroke="black" stroke-width="2"/>
  <!-- Create bars for ALL data points -->
  <rect x="60" y="250" width="35" height="100" fill="#2196F3"/>
  <rect x="100" y="240" width="35" height="110" fill="#2196F3"/>
  <!-- ... continue for ALL hours -->
  <!-- Add labels for ALL bars -->
</svg>
```

COMPREHENSIVE REPORT STRUCTURE:

# [Descriptive Title Based on Data]

## Executive Summary
[Synthesize insights from ALL available data - 2-3 rich paragraphs covering all major patterns]

## Key Findings & Insights
- **Finding 1**: [Major insight from data analysis]
- **Finding 2**: [Pattern discovered across datasets]
- **Finding 3**: [Correlation or trend identified]
- **Finding 4**: [Additional insight]
[Include 5-8 key findings derived from comprehensive data analysis]

## Detailed Weather Analysis

### Temperature Patterns

**Table 1: Hourly Temperature Forecast**
[Complete markdown table with ALL hourly temperature data]

**Chart 1: Temperature Progression Throughout the Day**
<svg>...</svg>
[Complete SVG showing temperature trend]

**Analysis:** [Detailed explanation of temperature patterns, peaks, troughs, and what they mean]

### Wind Conditions

**Table 2: Wind Speed and Direction Data**
[Complete markdown table with ALL wind data]

**Chart 2: Wind Speed Variations**
<svg>...</svg>
[Complete SVG showing wind patterns]

**Analysis:** [Explanation of wind conditions and patterns]

### Atmospheric Humidity

**Table 3: Humidity Levels Throughout the Day**
[Complete markdown table]

**Chart 3: Humidity Trend Analysis**
<svg>...</svg>

**Analysis:** [Explanation of humidity patterns]

### Precipitation Forecast

**Table 4: Precipitation Probability by Hour**
[Complete markdown table]

**Chart 4: Rain Probability Throughout the Day**
<svg>...</svg>

**Analysis:** [Explanation of precipitation likelihood]

### Temperature Perception

**Table 5: Actual vs Feels Like Temperature**
[Comparative markdown table]

**Chart 5: Temperature Comparison (Actual vs Perceived)**
<svg>...</svg>
[Multi-line chart comparing actual and feels-like temperatures]

**Analysis:** [Explanation of wind chill and perceived temperature]

### Wind Gusts

**Table 6: Wind Gust Measurements**
[Complete markdown table]

**Chart 6: Wind Gust Intensity**
<svg>...</svg>

**Analysis:** [Explanation of gust patterns and safety implications]

### UV Exposure

**Table 7: UV Index Throughout the Day**
[Complete markdown table]

**Chart 7: UV Risk Levels**
<svg>...</svg>

**Analysis:** [Explanation of UV exposure and recommendations]

### Visibility Conditions

**Table 8: Visibility Measurements**
[Complete markdown table]

**Chart 8: Visibility Trends**
<svg>...</svg>

**Analysis:** [Explanation of visibility conditions]

### [Additional Datasets]
[Continue with any other datasets found in the tables]

## Multi-Day Forecast Comparison
[If data includes multiple days]

**Table X: Extended Forecast**
[Comparative table across multiple days]

**Chart X: Multi-Day Weather Trends**
<svg>...</svg>

**Analysis:** [Comparison and trends across days]

## Comprehensive Analysis
[Deep dive into patterns, correlations, and insights discovered across ALL datasets]

### Weather Patterns
[Analysis of overall weather patterns from the data]

### Optimal Times for Activities
[Based on the data, suggest best times for outdoor activities]

### Notable Trends
[Highlight interesting trends discovered in the data]

## Additional Context
[Any supplementary information from the scraped content]

## Conclusions
[Summary of all key takeaways from the comprehensive data analysis]

---

## Sources & References
[List all sources with links]

⚠️ CRITICAL REQUIREMENTS CHECKLIST:
□ Created 5-8+ different SVG charts (minimum)
□ Each chart visualizes different data
□ Every chart has a corresponding complete markdown table
□ All tables include ALL rows (no truncation)
□ Used data from multiple tables in the source
□ Charts use appropriate types (line, bar, multi-line, etc.)
□ Analysis provided for each visualization
□ Comprehensive insights drawn from ALL available data

If you haven't met ALL these requirements, you have not completed the task correctly.

Generate the COMPLETE Markdown report (output ONLY the Markdown):"""

        # Add to conversation history
        if not self.conversation_history:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Generate with GPT-4o
        start_time = datetime.now()
        
        # response = await client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=self.conversation_history,
        #     max_tokens=4000,
        #     temperature=0.7
        # )
        
        response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16000,
        temperature=0.7,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
         
        # markdown_content = response.content[0].message.content.strip()
        markdown_content = response.content[0].text.strip()
        # Clean up markdown code blocks
        if markdown_content.startswith("```markdown"):
            markdown_content = markdown_content[11:]
        elif markdown_content.startswith("```md"):
            markdown_content = markdown_content[5:]
        elif markdown_content.startswith("```"):
            markdown_content = markdown_content[3:]
        if markdown_content.endswith("```"):
            markdown_content = markdown_content[:-3]
        markdown_content = markdown_content.strip()
        
        # Validate it's markdown
        if not markdown_content.startswith("#") and "##" not in markdown_content[:500]:
            self._log("WARNING", "Generated content doesn't look like Markdown, wrapping with header")
            markdown_content = f"# Generated Report\n\n{markdown_content}"
        
        # Store state
        self.current_markdown = markdown_content
        
        # Add summary to conversation
        summary = f"Generated Markdown report with requested features."
        if search_results:
            total_results = sum(len(r) for r in search_results.values())
            summary += f" Used {len(search_results)} search queries with {total_results} results."
        if scraped_results:
            successful = len([s for s in scraped_results if not s.get('error')])
            total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
            summary += f" Scraped {successful} pages with {total_tables} tables extracted."
            summary += f" Created comprehensive visualizations for multiple datasets."
        if structured_data:
            summary += f" Extracted structured data with {len(structured_data)} data categories."
        
        self.conversation_history.append({
            "role": "assistant",
            "content": summary
        })
        
        return markdown_content
    
    async def _generate_markdown(
        self,
        user_query: str,
        search_results: Dict[str, List[Dict]],
        scraped_results: List[Dict],
        structured_data: Dict
    ) -> str:
        """
        Generate comprehensive Markdown report with tables and analysis.
        NO SVG charts in markdown - those will be generated in HTML conversion step.
        """
        
        is_update = self.current_markdown is not None
        
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
                scraped_context += f"Tables Found: {scrape.get('tables_count', 0)}\n"
                
                if scrape.get('best_chunk'):
                    scraped_context += f"\nMost Relevant Content:\n"
                    scraped_context += "```\n"
                    scraped_context += scrape['best_chunk'][:3000]
                    if len(scrape['best_chunk']) > 3000:
                        scraped_context += "\n... (truncated)"
                    scraped_context += "\n```\n"
                
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
            structured_context += "\n\nThis is pre-extracted, structured data. Use these exact values in your report."
        
        # System prompt for markdown generation
        system_prompt = """You are an expert data analyst who creates comprehensive, well-structured markdown reports.

Your reports are:
- Detailed and exhaustive (use ALL provided data)
- Well-organized with clear hierarchy
- Data-rich with complete tables
- Analytical with insights and patterns
- Professional and informative

You create markdown with:
- Clear section headers (##, ###)
- Complete markdown tables with ALL data
- Bullet lists for key findings
- Descriptive text explaining data and insights
- Proper formatting and structure
- Source citations with links"""

        # Count data for accountability
        num_scraped = len([s for s in scraped_results if not s.get('error')])
        num_tables = sum(s.get('tables_count', 0) for s in scraped_results)
        num_words = sum(s.get('word_count', 0) for s in scraped_results)
        
        # Build user prompt
        if is_update:
            user_prompt = f"""Update the following Markdown report based on this request:

USER REQUEST: {user_query}

CURRENT MARKDOWN REPORT:
{self.current_markdown}
{search_context}
{scraped_context}
{structured_context}

YOUR TASK: Update the markdown report with new information while preserving existing content.

REQUIREMENTS:
1. Use ALL tables provided - create complete markdown tables for each
2. Include ALL text content from scraped sources in explanatory sections
3. Create narrative sections that analyze and explain the data
4. Add executive summary synthesizing key insights
5. Include source links at the end

OUTPUT: Complete markdown report (output ONLY the markdown):"""
        else:
            user_prompt = f"""Create a comprehensive Markdown report based on this request:

USER REQUEST: {user_query}
{search_context}
{scraped_context}
{structured_context}

DATA INVENTORY:
- Scraped Pages: {num_scraped}
- Total Tables: {num_tables}
- Total Content: {num_words} words
- Search Results: {sum(len(r) for r in search_results.values()) if search_results else 0}
- Structured Data: {len(structured_data) if structured_data else 0} categories

YOUR TASK: Create an exhaustive markdown report using ALL the data above.

CRITICAL REQUIREMENTS:

1. **PROCESS ALL TABLES**
   - You have {num_tables} tables from the scraped data
   - Create a complete markdown table for EACH one
   - Include ALL rows and columns (no truncation)
   - Add descriptive headers for each table

2. **USE ALL TEXT CONTENT**
   - You have {num_words} words of scraped content
   - Include this text in explanatory sections
   - Create narrative flow between data sections
   - Add analysis and commentary

3. **COMPREHENSIVE STRUCTURE**

Your markdown report MUST include:

## Executive Summary
[2-4 paragraphs synthesizing insights from ALL data]

## Key Findings
- Finding 1: [Major insight from data]
- Finding 2: [Pattern discovered]
- Finding 3: [Trend identified]
[5-10 bullet points of key insights]

## Detailed Analysis

### Dataset 1: [Descriptive Name]

**Overview**
[Brief description of what this dataset contains]

**Data Table**

| Column 1 | Column 2 | Column 3 | Column 4 |
|----------|----------|----------|----------|
| Value 1  | Value 2  | Value 3  | Value 4  |
| Value 5  | Value 6  | Value 7  | Value 8  |
[... ALL rows - NO truncation ...]

**Analysis**
[Paragraph explaining patterns, trends, insights from this data]

### Dataset 2: [Descriptive Name]
[Repeat structure for EACH table]

### Dataset 3: [Descriptive Name]
[Continue for ALL datasets]

## Additional Insights
[Text content from scraped sources - explanations, context, commentary]

## Comparisons & Correlations
[If applicable, compare datasets and identify patterns]

## Conclusions
[Summarize all findings and key takeaways]

## Sources & References
- [Source 1 name](URL)
- [Source 2 name](URL)
[List all sources]

4. **MARKDOWN TABLE FORMAT**

Use proper markdown table syntax:
```
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```

5. **CRITICAL RULES**
- NO placeholders like "... (more data)" or "etc."
- NO comments like "Additional rows omitted"
- INCLUDE every row of every table
- USE all text content from best_chunk fields
- CREATE analysis for every dataset
- MAKE it comprehensive and exhaustive

6. **QUALITY STANDARDS**
- Professional writing
- Clear explanations
- Data-driven insights
- Logical organization
- Complete coverage of all data

Generate the COMPLETE Markdown report now.
Output ONLY the markdown (no explanations, no code blocks wrapping it):"""
        
        # Add to conversation history
        if not self.conversation_history:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Generate with GPT-4o
        # start_time = datetime.now()
        
        # response = await client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=self.conversation_history,
        #     max_tokens=16000,  # Increased for comprehensive reports
        #     temperature=0.7
        # )
        
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        markdown_content = response.content[0].text.strip()
        
        # markdown_content = response.choices[0].message.content.strip()
        
        # Clean up markdown code blocks if wrapped
        if markdown_content.startswith("```markdown"):
            markdown_content = markdown_content[11:]
        elif markdown_content.startswith("```md"):
            markdown_content = markdown_content[5:]
        elif markdown_content.startswith("```"):
            markdown_content = markdown_content[3:]
        if markdown_content.endswith("```"):
            markdown_content = markdown_content[:-3]
        markdown_content = markdown_content.strip()
        
        # Validate it's markdown
        if not markdown_content.startswith("#") and "##" not in markdown_content[:500]:
            self._log("WARNING", "Generated content doesn't look like Markdown, adding header")
            markdown_content = f"# Generated Report\n\n{markdown_content}"
        
        # Store state
        self.current_markdown = markdown_content
        
        # Add summary to conversation
        summary = f"Generated comprehensive markdown report."
        if search_results:
            total_results = sum(len(r) for r in search_results.values())
            summary += f" Used {len(search_results)} search queries with {total_results} results."
        if scraped_results:
            successful = len([s for s in scraped_results if not s.get('error')])
            total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
            summary += f" Processed {successful} pages with {num_tables} tables - all converted to markdown tables."
        if structured_data:
            summary += f" Utilized structured data."
        
        self.conversation_history.append({
            "role": "assistant",
            "content": summary
        })
        # yield {"type":"markdown","content":markdown_content}
        return markdown_content
    
    def save_markdown_report(self, markdown_content: str) -> str:
        """Save Markdown to file"""
        self.iteration_count += 1
        filename = f"report_{self.iteration_count}.md"
        filepath = Path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(filepath.absolute())

    def save_reasoning_logs(self, filename: str = "reasoning_log.json"):
        """Save reasoning logs to JSON"""
        if self.reasoning_logs:
            with open(filename, 'w') as f:
                json.dump(self.reasoning_logs, f, indent=2)
            # print(f"\n✅ Reasoning logs saved to {filename}")
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