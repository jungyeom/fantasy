#!/usr/bin/env python3
"""Debug script to examine Yahoo DFS HTML structure."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection.collectors import YahooDFSCollector
from data_collection.base import SportType


async def debug_yahoo():
    """Debug Yahoo DFS HTML structure."""
    collector = YahooDFSCollector()
    
    try:
        print("🔍 Debugging Yahoo DFS HTML structure...")
        
        # Get the NFL page
        sport_url = "/nfl"
        full_url = f"{collector.config.base_url}{sport_url}"
        print(f"📡 Fetching: {full_url}")
        
        html_content = await collector._get_page_content(full_url)
        soup = await collector._parse_html(html_content)
        
        print(f"📄 HTML length: {len(html_content)} characters")
        
        # Look for contest-related elements
        print("\n🔍 Searching for contest containers...")
        
        # Method 1: Look for common contest container patterns
        selectors = [
            '[class*="contest"]',
            '[class*="tournament"]', 
            '[class*="game"]',
            '[data-testid*="contest"]',
            '[data-testid*="tournament"]',
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            print(f"  {selector}: {len(elements)} elements")
        
        # Method 2: Look for elements with contest-related text
        contest_text_elements = soup.find_all(text=lambda text: text and any(word in text.lower() for word in ['contest', 'tournament', 'game', 'entry fee', 'prize pool']))
        print(f"\n📝 Elements with contest-related text: {len(contest_text_elements)}")
        
        # Show first few contest-related text elements
        for i, elem in enumerate(contest_text_elements[:10]):
            text = elem.strip() if elem else ""
            if len(text) > 20:  # Only show meaningful text
                print(f"  {i+1}. {text[:100]}...")
        
        # Method 3: Look for table rows or list items
        contest_containers = []
        for element in soup.find_all(['tr', 'li', 'div']):
            text = element.get_text().lower()
            if any(word in text for word in ['entry fee', 'prize pool', 'max entries', 'guaranteed']):
                contest_containers.append(element)
        
        print(f"\n📊 Found {len(contest_containers)} potential contest containers")
        
        # Examine first few containers
        for i, container in enumerate(contest_containers[:3]):
            print(f"\n📦 Container {i+1}:")
            print(f"  Tag: {container.name}")
            print(f"  Classes: {container.get('class', [])}")
            print(f"  Text preview: {container.get_text()[:200]}...")
            
            # Look for specific data
            text = container.get_text()
            
            # Try to find entry fee
            import re
            fee_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
            if fee_match:
                print(f"  💰 Entry fee found: ${fee_match.group(1)}")
            
            # Try to find prize pool
            pool_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:prize|pool|guaranteed)', text, re.I)
            if pool_match:
                print(f"  🏆 Prize pool found: {pool_match.group(1)}")
            
            # Try to find entry limits
            limit_match = re.search(r'(\d+)\s*entries?', text, re.I)
            if limit_match:
                print(f"  📊 Entry limit found: {limit_match.group(1)}")
        
        # Look for JavaScript data
        print("\n🔍 Searching for JavaScript data...")
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('contest' in script.string.lower() or 'tournament' in script.string.lower()):
                print(f"  📜 Script with contest data found: {len(script.string)} chars")
                
                # Look for more specific patterns
                import re
                
                # Look for contest data patterns
                contest_patterns = [
                    r'contest[":\s]+([^,}]+)',
                    r'tournament[":\s]+([^,}]+)',
                    r'entry[":\s]+([^,}]+)',
                    r'fee[":\s]+([^,}]+)',
                    r'prize[":\s]+([^,}]+)',
                    r'pool[":\s]+([^,}]+)',
                    r'guaranteed[":\s]+([^,}]+)',
                ]
                
                for pattern in contest_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    if matches:
                        print(f"    {pattern}: {len(matches)} matches")
                        for match in matches[:3]:
                            print(f"      {match[:50]}...")
                
                # Look for JSON-like data with contest info
                json_matches = re.findall(r'\{[^{}]*"contest"[^{}]*\}', script.string)
                if json_matches:
                    print(f"    Found {len(json_matches)} potential JSON objects")
                    for match in json_matches[:2]:
                        print(f"      {match[:100]}...")
                
                # Look for larger JSON objects that might contain contest arrays
                large_json = re.findall(r'\{[^{}]{100,}[^{}]*\}', script.string)
                contest_jsons = [j for j in large_json if 'contest' in j.lower() or 'tournament' in j.lower()]
                if contest_jsons:
                    print(f"    Found {len(contest_jsons)} large JSON objects with contest data")
                    for i, json_str in enumerate(contest_jsons[:2]):
                        print(f"      JSON {i+1}: {json_str[:200]}...")
                        
                        # Try to extract specific contest data
                        try:
                            import json
                            # Clean up the JSON string
                            cleaned = re.sub(r'[^\x20-\x7E]', '', json_str)
                            # Try to find valid JSON
                            json_start = cleaned.find('{')
                            json_end = cleaned.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                potential_json = cleaned[json_start:json_end]
                                try:
                                    parsed = json.loads(potential_json)
                                    print(f"        Successfully parsed JSON with keys: {list(parsed.keys())}")
                                except json.JSONDecodeError:
                                    print(f"        JSON parse failed, but found structure")
                        except Exception as e:
                            print(f"        JSON extraction error: {e}")
                
                # Look for specific contest data patterns
                print("\n🔍 Looking for specific contest data patterns...")
                
                # Entry fees
                fee_patterns = [
                    r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'entry[":\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'fee[":\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
                ]
                
                for pattern in fee_patterns:
                    matches = re.findall(pattern, script.string)
                    if matches:
                        print(f"  Entry fees ({pattern}): {len(matches)} matches")
                        unique_fees = list(set(matches))[:5]
                        print(f"    Sample fees: {unique_fees}")
                
                # Prize pools
                pool_patterns = [
                    r'prize[":\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'pool[":\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'guaranteed[":\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:prize|pool|guaranteed)',
                ]
                
                for pattern in pool_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    if matches:
                        print(f"  Prize pools ({pattern}): {len(matches)} matches")
                        unique_pools = list(set(matches))[:5]
                        print(f"    Sample pools: {unique_pools}")
                
                # Entry limits
                limit_patterns = [
                    r'max[":\s]+(\d+)\s*entries?',
                    r'limit[":\s]+(\d+)\s*entries?',
                    r'entries?[":\s]+(\d+)',
                    r'(\d+)\s*entries?',
                ]
                
                for pattern in limit_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    if matches:
                        print(f"  Entry limits ({pattern}): {len(matches)} matches")
                        unique_limits = list(set(matches))[:5]
                        print(f"    Sample limits: {unique_limits}")
                
                # Contest names
                name_patterns = [
                    r'name[":\s]+([^,}"]+)',
                    r'title[":\s]+([^,}"]+)',
                    r'contest[":\s]+([^,}"]+)',
                ]
                
                for pattern in name_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    if matches:
                        print(f"  Contest names ({pattern}): {len(matches)} matches")
                        unique_names = list(set(matches))[:5]
                        print(f"    Sample names: {unique_names}")
                
                break  # Only examine the first large script
        
        # Look for data attributes
        print("\n🔍 Searching for data attributes...")
        data_elements = soup.find_all(attrs={'data-': True})
        print(f"  Elements with data attributes: {len(data_elements)}")
        
        for elem in data_elements[:5]:
            attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
            if attrs:
                print(f"    {elem.name}: {attrs}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await collector.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_yahoo()) 