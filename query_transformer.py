"""
Enhanced Query Transformer with Multi-Search Support

This transformer:
1. Detects when web search is needed with high accuracy
2. Generates MULTIPLE targeted search queries for complex requests
3. Identifies data extraction needs
4. Plans comprehensive research strategies
"""

import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict
# from openai import AsyncOpenAI
from typing import Optional
import os
from anthropic import AsyncAnthropic
key = os.getenv("LLM_API_KEY")
client = AsyncAnthropic(api_key=key)
 
class EnhancedQueryTransformer:
    """Advanced query transformation with multi-search support"""
    
    @staticmethod
    async def get_transformed_query(
        self,
        query: str,
        previous_queries: Optional[List[str]] = None
    ):
        """
        Transform user query into structured search plan with proper error handling
        
        Yields progress updates and final transformer output
        """
        
        if previous_queries is None:
            previous_queries = []
        
        # Build context from previous queries
        context = ""
        if previous_queries:
            context = "\n\nPrevious queries in this conversation:\n"
            for i, prev_q in enumerate(previous_queries[-3:], 1):
                context += f"{i}. {prev_q}\n"
        
        prompt = f"""Analyze this user query and determine the best search strategy.

USER QUERY: "{query}"{context}

YOUR TASK: Return a JSON object with this EXACT structure:

{{
    "web_search_needed": true,
    "search_queries": [
        "specific search query 1",
        "specific search query 2",
        "specific search query 3"
    ],
    "data_extraction_needed": true,
    "data_types": ["statistics", "comparisons", "trends"]
}}

RULES:
1. web_search_needed: true if query needs current/factual info, false for creative/opinion tasks
2. search_queries: List 3-5 specific, targeted search queries (NOT the original query)
3. data_extraction_needed: true if expecting structured data (numbers, tables, comparisons)
4. data_types: List what data to extract: ["statistics", "dates", "names", "prices", etc]

IMPORTANT:
- Return ONLY valid JSON, no explanations
- Use double quotes, not single quotes
- Use lowercase true/false, not True/False
- Make search queries specific and targeted
- If no web search needed, return empty search_queries array

Examples:

Query: "What's the weather in Paris?"
{{
    "web_search_needed": true,
    "search_queries": ["Paris weather current", "Paris temperature today"],
    "data_extraction_needed": true,
    "data_types": ["temperature", "conditions"]
}}

Query: "Write me a poem about cats"
{{
    "web_search_needed": false,
    "search_queries": [],
    "data_extraction_needed": false,
    "data_types": []
}}

Query: "Compare GDP of US vs China in 2024"
{{
    "web_search_needed": true,
    "search_queries": ["United States GDP 2024", "China GDP 2024", "US China GDP comparison 2024"],
    "data_extraction_needed": true,
    "data_types": ["statistics", "gdp", "comparisons", "economic_data"]
}}

Now analyze the user's query and return ONLY the JSON:"""

        try:
            # Call Claude API
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract response text
            extracted_text = response.content[0].text.strip()
            
            print(f"[TRANSFORMER] Raw response: {extracted_text[:200]}")
            
            # ============================================================================
            # STEP 1: Clean markdown code blocks
            # ============================================================================
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text[7:]
            elif extracted_text.startswith("```"):
                extracted_text = extracted_text[3:]
            
            if extracted_text.endswith("```"):
                extracted_text = extracted_text[:-3]
            
            extracted_text = extracted_text.strip()
            
            # ============================================================================
            # STEP 2: Fix Python dict notation → Valid JSON
            # ============================================================================
            # Replace single quotes with double quotes (Python dict → JSON)
            extracted_text = extracted_text.replace("'", '"')
            
            # Replace Python booleans with JSON booleans
            extracted_text = extracted_text.replace('True', 'true')
            extracted_text = extracted_text.replace('False', 'false')
            extracted_text = extracted_text.replace('None', 'null')
            
            print(f"[TRANSFORMER] Cleaned: {extracted_text[:200]}")
            
            # ============================================================================
            # STEP 3: Parse JSON with error handling
            # ============================================================================
            try:
                extracted_data = json.loads(extracted_text)
                print(f"[TRANSFORMER] ✅ Successfully parsed JSON")
                
            except json.JSONDecodeError as e:
                print(f"[TRANSFORMER] ❌ JSON parsing error: {e}")
                print(f"[TRANSFORMER] Problematic text: {extracted_text[:500]}")
                
                # Try to extract key-value pairs manually as fallback
                try:
                    # Attempt basic parsing for common patterns
                    import re
                    
                    # Extract web_search_needed
                    web_search_match = re.search(r'"web_search_needed":\s*(true|false)', extracted_text, re.IGNORECASE)
                    web_search_needed = web_search_match.group(1).lower() == 'true' if web_search_match else True
                    
                    # Extract search_queries array
                    queries_match = re.search(r'"search_queries":\s*\[(.*?)\]', extracted_text, re.DOTALL)
                    search_queries = []
                    if queries_match:
                        queries_str = queries_match.group(1)
                        # Extract strings from array
                        search_queries = re.findall(r'"([^"]+)"', queries_str)
                    
                    # If no queries extracted, use original query as fallback
                    if not search_queries and web_search_needed:
                        search_queries = [query]
                    
                    extracted_data = {
                        "web_search_needed": web_search_needed,
                        "search_queries": search_queries,
                        "data_extraction_needed": True,
                        "data_types": ["general"]
                    }
                    
                    print(f"[TRANSFORMER] ⚠️ Used fallback parsing: {extracted_data}")
                    
                except Exception as fallback_error:
                    print(f"[TRANSFORMER] ❌ Fallback parsing also failed: {fallback_error}")
                    
                    # Ultimate fallback - just search the original query
                    extracted_data = {
                        "web_search_needed": True,
                        "search_queries": [query],
                        "data_extraction_needed": False,
                        "data_types": []
                    }
                    
                    print(f"[TRANSFORMER] 🆘 Using ultimate fallback")
            
            # ============================================================================
            # STEP 4: Normalize and validate data
            # ============================================================================
            
            # Ensure web_search_needed is boolean
            if isinstance(extracted_data.get('web_search_needed'), str):
                extracted_data['web_search_needed'] = extracted_data['web_search_needed'].lower() in ['true', '1', 'yes']
            
            # Ensure search_queries is a list
            if not isinstance(extracted_data.get('search_queries'), list):
                extracted_data['search_queries'] = []
            
            # Ensure data_extraction_needed is boolean
            if isinstance(extracted_data.get('data_extraction_needed'), str):
                extracted_data['data_extraction_needed'] = extracted_data['data_extraction_needed'].lower() in ['true', '1', 'yes']
            
            # Ensure data_types is a list
            if not isinstance(extracted_data.get('data_types'), list):
                extracted_data['data_types'] = []
            
            # Remove empty queries
            extracted_data['search_queries'] = [q for q in extracted_data['search_queries'] if q and q.strip()]
            
            # If web search needed but no queries, use original query
            if extracted_data.get('web_search_needed') and not extracted_data['search_queries']:
                extracted_data['search_queries'] = [query]
                print(f"[TRANSFORMER] ⚠️ No search queries provided, using original query")
            
            # ============================================================================
            # STEP 5: Log and yield results
            # ============================================================================
            
            print(f"[TRANSFORMER] Final output:")
            print(f"  - Web search needed: {extracted_data['web_search_needed']}")
            print(f"  - Search queries: {len(extracted_data['search_queries'])}")
            print(f"  - Data extraction: {extracted_data.get('data_extraction_needed', False)}")
            
            # Yield progress update
            if extracted_data['web_search_needed']:
                yield {
                    "type": "transformed_query",
                    "content": f"Planning research with {len(extracted_data['search_queries'])} search angles"
                }
            else:
                yield {
                    "type": "transformed_query",
                    "content": "No web research needed for this query"
                }
            
            # Yield final result
            yield {
                "type": "transformer_output",
                "content": extracted_data
            }
            
        except Exception as e:
            print(f"[TRANSFORMER] ❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback
            fallback_data = {
                "web_search_needed": True,
                "search_queries": [query],
                "data_extraction_needed": False,
                "data_types": []
            }
            
            print(f"[TRANSFORMER] 🆘 Emergency fallback activated")
            
            yield {
                "type": "transformed_query",
                "content": "Using fallback search strategy"
            }
            
            yield {
                "type": "transformer_output",
                "content": fallback_data
            }
    
    @staticmethod
    def _clean_query_dates(query: str, date_context: Dict) -> str:
        """Remove old dates from training data and replace temporal keywords"""
        
        original_query = query
        cleaned_query = query
        
        # Replace temporal keywords with actual dates/terms
        cleaned_query = cleaned_query.replace('today', date_context['today'])
        cleaned_query = cleaned_query.replace('Today', date_context['today'])
        cleaned_query = cleaned_query.replace('this year', str(date_context['current_year']))
        cleaned_query = cleaned_query.replace('current year', str(date_context['current_year']))
        
        # Remove old years from training data (2020-2024)
        # Pattern 1: "October 5 2023" or "October 5, 2023"
        cleaned_query = re.sub(
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}[,\s]+202[0-4]\b',
            '',
            cleaned_query,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: "2023-10-05" or "2023/10/05"
        cleaned_query = re.sub(r'\b202[0-4][-/]\d{2}[-/]\d{2}\b', '', cleaned_query)
        
        # Pattern 3: Just the year "2023" or "2024" (but not in valid contexts like "2023-2025")
        cleaned_query = re.sub(r'\b202[0-4](?!\s*[-–]\s*\d{4})\b', '', cleaned_query)
        
        # Pattern 4: "5 October 2023"
        cleaned_query = re.sub(
            r'\b\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+202[0-4]\b',
            '',
            cleaned_query,
            flags=re.IGNORECASE
        )
        
        # Clean up extra spaces and trim
        cleaned_query = ' '.join(cleaned_query.split())
        cleaned_query = cleaned_query.strip()
        
        if original_query != cleaned_query:
            print(f"[TRANSFORMER] Cleaned dates: '{original_query}' → '{cleaned_query}'")
        
        return cleaned_query


# Backward compatibility wrapper
class QueryTransformer:
    """Wrapper for backward compatibility with old single-query interface"""
    
    @staticmethod
    async def get_transformed_query(
        user_query: str, 
        past_user_queries: List[str]
    ) -> dict:
        """
        Returns format compatible with old code (single search_query)
        Use EnhancedQueryTransformer directly for multi-query support
        """
        result = await EnhancedQueryTransformer.get_transformed_query(
            user_query, 
            past_user_queries
        )
        
        # Convert to old format (take first query only)
        return {
            "web_search_needed": result["web_search_needed"],
            "search_query": result["search_queries"][0] if result["search_queries"] else ""
        }