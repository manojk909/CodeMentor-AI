import random
import requests
import time
from datetime import datetime, timedelta
from app.models import PlatformStats, Problem, ProblemSolved
from app import db

class CodingTracker:
    """Service for tracking coding progress across platforms"""
    
    def __init__(self):
        self.platforms = {
            'leetcode': {
                'name': 'LeetCode',
                'color': '#FFA500',
                'icon': 'code'
            },
            'geeksforgeeks': {
                'name': 'GeeksforGeeks',
                'color': '#2F8D46',
                'icon': 'book'
            },
            'hackerrank': {
                'name': 'HackerRank',
                'color': '#2EC866',
                'icon': 'trophy'
            },
            'github': {
                'name': 'GitHub',
                'color': '#333333',
                'icon': 'github'
            }
        }
    
    def sync_platform_data(self, user_id, platform, username):
        """Sync data from a coding platform with real data scraping"""
        if platform not in self.platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        try:
            # Try to get real data first
            if platform == 'leetcode':
                platform_data = self._scrape_leetcode_data(username)
            elif platform == 'geeksforgeeks':
                platform_data = self._scrape_geeksforgeeks_data(username)
            elif platform == 'github':
                platform_data = self._scrape_github_data(username)
            elif platform == 'hackerrank':
                platform_data = self._scrape_hackerrank_data(username)
            else:
                # Fallback to mock data if scraping not available
                platform_data = self._generate_mock_platform_data(platform)
        except Exception as e:
            print(f"Error scraping {platform} data for {username}: {e}")
            # Fallback to mock data on error
            platform_data = self._generate_mock_platform_data(platform)
        
        # Update or create platform stats
        stats = PlatformStats.query.filter_by(user_id=user_id, platform=platform).first()
        if not stats:
            stats = PlatformStats()
            stats.user_id = user_id
            stats.platform = platform
            db.session.add(stats)
        
        # Update stats with scraped data
        stats.total_problems = platform_data['total_problems']
        stats.basic_solved = platform_data.get('basic_solved', 0)  # Include basic problems
        stats.easy_solved = platform_data['easy_solved']
        stats.medium_solved = platform_data['medium_solved']
        stats.hard_solved = platform_data['hard_solved']
        stats.contest_rating = platform_data.get('contest_rating', 0)
        stats.streak = platform_data.get('streak', 0)
        stats.last_updated = datetime.utcnow()
        
        # Add some sample problems if they don't exist (not for GitHub)
        if platform != 'github':
            self._add_sample_problems(platform)
        
        db.session.commit()
        return stats
    
    def _scrape_leetcode_data(self, username):
        """Scrape LeetCode data using GraphQL API and web scraping for streak"""
        try:
            # First get data via GraphQL API
            url = "https://leetcode.com/graphql"
            
            query = """
            query userProfile($username: String!) {
                matchedUser(username: $username) {
                    submitStats {
                        acSubmissionNum {
                            difficulty
                            count
                        }
                    }
                    profile {
                        ranking
                        realName
                    }
                }
            }
            """
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            payload = {
                'query': query,
                'variables': {'username': username}
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code != 200:
                raise Exception(f"HTTP error: {response.status_code}")
                
            data = response.json()
            
            # Initialize default values
            easy_solved = 0
            medium_solved = 0
            hard_solved = 0
            ranking = 0
            streak = 0
            
            if 'data' in data and data['data'] and data['data']['matchedUser']:
                user_data = data['data']['matchedUser']
                submissions = user_data.get('submitStats', {}).get('acSubmissionNum', [])
                
                easy_solved = next((s['count'] for s in submissions if s['difficulty'] == 'Easy'), 0)
                medium_solved = next((s['count'] for s in submissions if s['difficulty'] == 'Medium'), 0)
                hard_solved = next((s['count'] for s in submissions if s['difficulty'] == 'Hard'), 0)
                
                profile_info = user_data.get('profile', {})
                ranking = profile_info.get('ranking', 0) if profile_info else 0
            
            # Enhanced streak scraping using requests with better session management
            try:
                print(f"Scraping LeetCode streak for user: {username}")
                streak = self._scrape_leetcode_streak_enhanced(username)
                if streak is not None:
                    print(f"Successfully scraped LeetCode streak: {streak}")
                else:
                    print("Could not scrape streak data, using fallback")
                    streak = 0
                    
            except Exception as e:
                print(f"Error in enhanced streak scraping: {e}")
                streak = 0
            
            return {
                'total_problems': easy_solved + medium_solved + hard_solved,
                'easy_solved': easy_solved,
                'medium_solved': medium_solved,
                'hard_solved': hard_solved,
                'contest_rating': ranking or 0,
                'streak': streak
            }
                
        except Exception as e:
            print(f"LeetCode scraping error for {username}: {e}")
            raise e
    
    def _scrape_leetcode_streak_enhanced(self, username):
        """Enhanced LeetCode streak scraping using requests with better session management"""
        try:
            import re
            from bs4 import BeautifulSoup
            import time
            
            # Create a session with better headers to mimic a real browser
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            
            session.headers.update(headers)
            
            # First, visit LeetCode homepage to establish session
            print("Establishing session with LeetCode...")
            homepage_response = session.get('https://leetcode.com/', timeout=15)
            time.sleep(2)  # Brief delay
            
            # Then visit the user profile
            profile_url = f"https://leetcode.com/{username}/"
            print(f"Fetching profile page: {profile_url}")
            response = session.get(profile_url, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                streak = None
                
                # Method 1: Look for exact HTML structure provided by user
                # <div class="space-x-1"><span class="text-label-3 dark:text-dark-label-3">Max streak:</span><span class="font-medium text-label-2 dark:text-dark-label-2">6</span></div>
                print("Searching for streak using exact HTML structure...")
                
                space_divs = soup.find_all('div', class_='space-x-1')
                print(f"Found {len(space_divs)} divs with space-x-1 class")
                
                for div in space_divs:
                    div_text = div.get_text()
                    if 'Max streak:' in div_text:
                        print(f"Found Max streak div: {div_text}")
                        # Look for span with font-medium and text-label-2 classes
                        value_spans = div.find_all('span', class_=lambda x: x and 'font-medium' in x and 'text-label-2' in x)
                        
                        if not value_spans:
                            # Fallback to any span with font-medium
                            value_spans = div.find_all('span', class_=lambda x: x and 'font-medium' in x)
                        
                        for span in value_spans:
                            try:
                                span_text = span.get_text().strip()
                                print(f"Checking span text: '{span_text}'")
                                if span_text.isdigit():
                                    streak = int(span_text)
                                    print(f"Successfully found streak: {streak}")
                                    break
                            except (ValueError, AttributeError):
                                continue
                        
                        if streak is not None:
                            break
                
                # Method 2: Look for "X day streak" pattern (like "0 day streak" from screenshot)
                if streak is None:
                    print("Searching for 'day streak' pattern...")
                    day_streak_pattern = re.compile(r'(\d+)\s+day\s+streak', re.IGNORECASE)
                    matches = day_streak_pattern.findall(response.text)
                    if matches:
                        try:
                            streak = int(matches[0])
                            print(f"Found streak using 'day streak' pattern: {streak}")
                        except (ValueError, IndexError):
                            pass
                
                # Method 3: Alternative approach using regex on the entire HTML
                if streak is None:
                    print("Trying regex approach on page source...")
                    page_content = str(soup)
                    
                    # Look for the specific pattern in HTML
                    patterns = [
                        r'Max streak[:\s]*</span>\s*<span[^>]*>(\d+)</span>',
                        r'Max streak[:\s]*[^>]*>(\d+)<',
                        r'streak[:\s]*[^>]*>(\d+)<',
                        r'(\d+)\s*day\s*streak',
                        r'streak[:\s]*(\d+)',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
                        if matches:
                            try:
                                streak = int(matches[0])
                                print(f"Found streak using regex pattern '{pattern}': {streak}")
                                break
                            except (ValueError, IndexError):
                                continue
                
                # Method 4: Look for any numerical value near "streak" text
                if streak is None:
                    print("Trying broader search for streak information...")
                    # Find all text containing "streak"
                    streak_elements = soup.find_all(string=re.compile(r'streak', re.IGNORECASE))
                    
                    for element in streak_elements:
                        parent = element.parent
                        if parent:
                            # Look for numbers in parent or sibling elements
                            for sibling in parent.find_all(['span', 'div']):
                                sibling_text = sibling.get_text().strip()
                                if sibling_text.isdigit() and 0 <= int(sibling_text) <= 365:
                                    streak = int(sibling_text)
                                    print(f"Found streak via text search: {streak}")
                                    break
                        
                        if streak is not None:
                            break
                
                # Method 5: Debug - print all elements that might contain streak info
                if streak is None:
                    print("Debug: Looking for all potential streak-related content...")
                    all_text = soup.get_text()
                    
                    # Search for any mention of "streak" and surrounding context
                    streak_contexts = []
                    for match in re.finditer(r'.{0,50}streak.{0,50}', all_text, re.IGNORECASE):
                        context = match.group(0).strip()
                        streak_contexts.append(context)
                        print(f"Found streak context: {context}")
                        
                        # Try to extract number from this context
                        numbers = re.findall(r'\d+', context)
                        for num in numbers:
                            if 0 <= int(num) <= 365:
                                streak = int(num)
                                print(f"Extracted streak from context: {streak}")
                                break
                        
                        if streak is not None:
                            break
                
                return streak
                
            else:
                print(f"Failed to load profile page, status code: {response.status_code}")
                if response.status_code == 403:
                    print("Access forbidden - LeetCode is blocking requests")
                return None
                
        except Exception as e:
            print(f"Enhanced streak scraping failed: {e}")
            return None
    
    def _scrape_geeksforgeeks_data(self, username):
        """Scrape GeeksforGeeks data using enhanced web scraping with HTML parsing"""
        try:
            import re
            from bs4 import BeautifulSoup
            
            # Extract username from URL if full URL is provided
            original_username = username
            if 'geeksforgeeks.org' in username:
                if '/user/' in username:
                    username = username.split('/user/')[-1].split('/')[0]
                elif '/profile/' in username:
                    username = username.split('/profile/')[-1].split('/')[0]
                # Remove any trailing slash or additional path
                username = username.rstrip('/').split('/')[0]
            
            # Clean username - handle edge cases
            if username.startswith('http'):
                # Extract username from malformed URLs
                username = username.replace('https://', '').replace('http://', '').replace('www.', '')
                username = username.split('/')[0] if '/' in username else username
            
            username = username.strip()
            
            # Validate username after cleaning
            if not username or username in ['https:', 'http:', ''] or len(username) < 2:
                raise Exception(f"Invalid username after cleaning: '{original_username}' -> '{username}'. Please provide a valid GeeksforGeeks username.")
            
            print(f"Extracting data for GeeksforGeeks user: {username}")
            
            # Try multiple profile URLs to get the best data
            urls_to_try = [
                f"https://auth.geeksforgeeks.org/user/{username}/practice/",
                f"https://auth.geeksforgeeks.org/user/{username}",
                f"https://www.geeksforgeeks.org/user/{username}/"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            session = requests.Session()
            soup = None
            
            # Try each URL until we find one that works
            for url in urls_to_try:
                try:
                    print(f"Trying URL: {url}")
                    response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        print(f"Successfully loaded page from: {url}")
                        break
                    else:
                        print(f"Failed to load {url}, status: {response.status_code}")
                except Exception as e:
                    print(f"Error with URL {url}: {e}")
                    continue
            
            if soup is None:
                raise Exception(f"Could not access GeeksforGeeks profile for '{username}'. Please check the username.")
            
            # Initialize variables
            total_problems = 0
            easy_solved = 0
            medium_solved = 0
            hard_solved = 0
            basic_solved = 0
            streak = 0
            rank = 0
            
            # Method 1: Extract data using the exact HTML selectors provided
            print("Looking for specific GeeksforGeeks elements...")
            
            # Total problems solved from scoreCard - skip first scoreCard and find "Problem Solved" section
            try:
                # Find all score cards
                score_cards = soup.find_all('div', {'class': 'scoreCard_head__nxXR8'})
                print(f"Found {len(score_cards)} scoreCards")
                
                # Skip the first scoreCard (which shows "58 solved" - the score/rating)
                # Look for "Problem Solved" text in the remaining cards
                for i, card in enumerate(score_cards):
                    if hasattr(card, 'find'):
                        # Look for the "Problem Solved" text
                        text_element = card.find('div', {'class': 'scoreCard_head_left--text__KZ2S1'})
                        if text_element and hasattr(text_element, 'get_text'):
                            text_content = text_element.get_text().strip()
                            print(f"ScoreCard {i+1} text: '{text_content}'")
                            
                            if 'Problem Solved' in text_content:
                                # Get the corresponding score
                                score_element = card.find('div', {'class': 'scoreCard_head_left--score__oSi_x'})
                                if score_element and hasattr(score_element, 'get_text'):
                                    try:
                                        total_problems = int(score_element.get_text().strip())
                                        print(f"Found total problems solved: {total_problems}")
                                        break
                                    except (ValueError, AttributeError):
                                        pass
                
                # Alternative approach: Skip first scoreCard and get second one if "Problem Solved" search fails
                if total_problems == 0 and len(score_cards) > 1:
                    print("Trying alternative approach: using second scoreCard")
                    second_card = score_cards[1]  # Skip first, use second
                    if hasattr(second_card, 'find'):
                        score_element = second_card.find('div', {'class': 'scoreCard_head_left--score__oSi_x'})
                        if score_element and hasattr(score_element, 'get_text'):
                            try:
                                total_problems = int(score_element.get_text().strip())
                                print(f"Found total problems from second scoreCard: {total_problems}")
                            except (ValueError, AttributeError):
                                pass
            except Exception as e:
                print(f"Error finding score element: {e}")
            
            # Difficulty breakdown from problemNavbar_head_nav--text__UaGCx elements
            try:
                nav_elements = soup.find_all('div', {'class': 'problemNavbar_head_nav--text__UaGCx'})
                for element in nav_elements:
                    try:
                        text = element.get_text().strip().upper()
                        print(f"Found nav element text: {text}")
                        
                        # Extract number from text like "BASIC (0)" or "EASY (3)"
                        match = re.search(r'\((\d+)\)', text)
                        if match:
                            count = int(match.group(1))
                            if 'BASIC' in text:
                                basic_solved = count
                                print(f"Found basic problems: {basic_solved}")
                            elif 'EASY' in text:
                                easy_solved = count
                                print(f"Found easy problems: {easy_solved}")
                            elif 'MEDIUM' in text:
                                medium_solved = count
                                print(f"Found medium problems: {medium_solved}")
                            elif 'HARD' in text:
                                hard_solved = count
                                print(f"Found hard problems: {hard_solved}")
                    except (AttributeError, ValueError) as e:
                        print(f"Error parsing nav element: {e}")
                        continue
            except Exception as e:
                print(f"Error finding nav elements: {e}")
            
            # Try to get rank from leaderboard page
            try:
                # First try to get rank from current page
                rank_element = soup.find('td', {'class': 'leaderboard_loggedin_user_rank_data__cH0OT'})
                if rank_element:
                    try:
                        rank = int(rank_element.get_text().strip())
                        print(f"Found rank: {rank}")
                    except (ValueError, AttributeError):
                        pass
                else:
                    # If not found, try to navigate to leaderboard page
                    leaderboard_url = f"https://practice.geeksforgeeks.org/leaderboard"
                    print(f"Trying leaderboard URL: {leaderboard_url}")
                    leaderboard_response = session.get(leaderboard_url, headers=headers, timeout=20)
                    if leaderboard_response.status_code == 200:
                        leaderboard_soup = BeautifulSoup(leaderboard_response.content, 'html.parser')
                        rank_element = leaderboard_soup.find('td', {'class': 'leaderboard_loggedin_user_rank_data__cH0OT'})
                        if rank_element:
                            try:
                                rank = int(rank_element.get_text().strip())
                                print(f"Found rank from leaderboard: {rank}")
                            except (ValueError, AttributeError):
                                pass
            except Exception as e:
                print(f"Error finding rank: {e}")
            
            # Get streak - try multiple selectors
            try:
                streak_selectors = [
                    'div.circularProgressBar_head_mid_streakCnt__MFOF1',
                    'div[class*="streak"]',
                    'span[class*="streak"]'
                ]
                
                for selector in streak_selectors:
                    streak_element = soup.select_one(selector)
                    if streak_element:
                        try:
                            streak_text = streak_element.get_text().strip()
                            # Extract just the first number before any slash
                            streak_match = re.match(r'(\d+)', streak_text)
                            if streak_match:
                                streak = int(streak_match.group(1))
                                print(f"Found streak: {streak}")
                                break
                        except (ValueError, AttributeError):
                            continue
            except Exception as e:
                print(f"Error finding streak element: {e}")
            
            # Ensure we have valid data
            if total_problems == 0:
                # If no total found but we have difficulty breakdown, calculate total
                total_problems = basic_solved + easy_solved + medium_solved + hard_solved
            
            # Return the extracted data
            print(f"Final GeeksforGeeks data: Total={total_problems}, Basic={basic_solved}, Easy={easy_solved}, Medium={medium_solved}, Hard={hard_solved}, Streak={streak}, Rank={rank}")
            
            return {
                'total_problems': total_problems,
                'basic_solved': basic_solved,  # Include basic problems count
                'easy_solved': easy_solved,
                'medium_solved': medium_solved,
                'hard_solved': hard_solved,
                'contest_rating': rank,  # Use rank as contest rating for GeeksforGeeks
                'streak': streak
            }
            
        except Exception as e:
            error_msg = f"GeeksforGeeks scraping failed for '{username}': {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    def _scrape_github_data(self, username):
        """Scrape GitHub data using GitHub API - showing repository and contribution stats"""
        try:
            # Get user stats
            user_url = f"https://api.github.com/users/{username}"
            response = requests.get(user_url, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Get repositories for additional stats
                repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"
                repos_response = requests.get(repos_url, timeout=10)
                repos_data = repos_response.json() if repos_response.status_code == 200 else []
                
                # Calculate meaningful GitHub metrics
                total_repos = user_data.get('public_repos', 0)
                total_stars = sum(repo.get('stargazers_count', 0) for repo in repos_data)
                total_forks = sum(repo.get('forks_count', 0) for repo in repos_data)
                followers = user_data.get('followers', 0)
                
                # Count repositories by type/activity
                active_repos = len([repo for repo in repos_data if not repo.get('fork', False)])
                forked_repos = len([repo for repo in repos_data if repo.get('fork', False)])
                
                # Calculate languages used (approximate)
                languages_count = len(set(repo.get('language') for repo in repos_data if repo.get('language')))
                
                return {
                    'total_problems': total_repos,  # Total Repositories
                    'easy_solved': active_repos,    # Original Repositories (not forks)
                    'medium_solved': total_stars,   # Total Stars Received
                    'hard_solved': followers,       # Followers Count
                    'contest_rating': languages_count,  # Programming Languages Used
                    'streak': total_forks           # Total Forks of Your Repos
                }
            else:
                raise Exception(f"GitHub user '{username}' not found or API error: {response.status_code}")
                
        except Exception as e:
            print(f"GitHub scraping error: {e}")
            raise e
    
    def _scrape_hackerrank_data(self, username):
        """Scrape HackerRank data"""
        try:
            # HackerRank doesn't have a public API, return mock data
            # In production, you'd need to implement web scraping or use unofficial APIs
            return self._generate_mock_platform_data('hackerrank')
            
        except Exception as e:
            print(f"HackerRank scraping error: {e}")
            raise e
    
    def _generate_mock_platform_data(self, platform):
        """Generate realistic mock data for platforms"""
        base_data = {
            'leetcode': {
                'total_problems': random.randint(50, 500),
                'easy_solved': random.randint(20, 150),
                'medium_solved': random.randint(15, 200),
                'hard_solved': random.randint(5, 100),
                'contest_rating': random.randint(1200, 2500),
                'streak': random.randint(0, 30)
            },
            'geeksforgeeks': {
                'total_problems': random.randint(30, 300),
                'basic_solved': random.randint(0, 20),  # Include basic problems in mock data
                'easy_solved': random.randint(15, 100),
                'medium_solved': random.randint(10, 150),
                'hard_solved': random.randint(5, 80),
                'contest_rating': 0,
                'streak': random.randint(0, 20)
            },
            'hackerrank': {
                'total_problems': random.randint(25, 200),
                'easy_solved': random.randint(10, 80),
                'medium_solved': random.randint(8, 100),
                'hard_solved': random.randint(2, 50),
                'contest_rating': random.randint(800, 2000),
                'streak': random.randint(0, 15)
            },
            'github': {
                'total_problems': random.randint(10, 100),  # Repositories
                'easy_solved': random.randint(50, 500),    # Commits this year
                'medium_solved': random.randint(5, 50),    # Pull requests
                'hard_solved': random.randint(1, 20),      # Major contributions
                'contest_rating': 0,
                'streak': random.randint(0, 100)  # Contribution streak
            }
        }
        
        return base_data.get(platform, base_data['leetcode'])
    
    def _add_sample_problems(self, platform):
        """Add sample problems for the platform if they don't exist"""
        sample_problems = {
            'leetcode': [
                {'title': 'Two Sum', 'difficulty': 'Easy', 'category': 'Array'},
                {'title': 'Add Two Numbers', 'difficulty': 'Medium', 'category': 'Linked List'},
                {'title': 'Longest Substring Without Repeating Characters', 'difficulty': 'Medium', 'category': 'String'},
                {'title': 'Median of Two Sorted Arrays', 'difficulty': 'Hard', 'category': 'Array'},
                {'title': 'Longest Palindromic Substring', 'difficulty': 'Medium', 'category': 'String'},
                {'title': 'Reverse Integer', 'difficulty': 'Easy', 'category': 'Math'},
                {'title': 'String to Integer (atoi)', 'difficulty': 'Medium', 'category': 'String'},
                {'title': 'Container With Most Water', 'difficulty': 'Medium', 'category': 'Array'},
                {'title': 'Regular Expression Matching', 'difficulty': 'Hard', 'category': 'Dynamic Programming'},
                {'title': 'Integer to Roman', 'difficulty': 'Medium', 'category': 'String'}
            ],
            'geeksforgeeks': [
                {'title': 'Find the Missing Number', 'difficulty': 'Easy', 'category': 'Array'},
                {'title': 'Binary Tree Traversal', 'difficulty': 'Medium', 'category': 'Tree'},
                {'title': 'Graph DFS and BFS', 'difficulty': 'Medium', 'category': 'Graph'},
                {'title': 'Dynamic Programming - LCS', 'difficulty': 'Hard', 'category': 'Dynamic Programming'},
                {'title': 'Sorting Algorithms', 'difficulty': 'Medium', 'category': 'Sorting'},
                {'title': 'Linked List Operations', 'difficulty': 'Easy', 'category': 'Linked List'},
                {'title': 'Stack and Queue Implementation', 'difficulty': 'Easy', 'category': 'Stack'},
                {'title': 'Hash Table Implementation', 'difficulty': 'Medium', 'category': 'Hashing'},
                {'title': 'Binary Search Variations', 'difficulty': 'Medium', 'category': 'Searching'},
                {'title': 'Greedy Algorithms', 'difficulty': 'Hard', 'category': 'Greedy'}
            ],
            'hackerrank': [
                {'title': 'Simple Array Sum', 'difficulty': 'Easy', 'category': 'Array'},
                {'title': 'Staircase', 'difficulty': 'Easy', 'category': 'Implementation'},
                {'title': 'Birthday Cake Candles', 'difficulty': 'Easy', 'category': 'Implementation'},
                {'title': 'Grading Students', 'difficulty': 'Easy', 'category': 'Implementation'},
                {'title': 'Apple and Orange', 'difficulty': 'Easy', 'category': 'Implementation'},
                {'title': 'Kangaroo', 'difficulty': 'Easy', 'category': 'Math'},
                {'title': 'Breaking the Records', 'difficulty': 'Easy', 'category': 'Implementation'},
                {'title': 'Birthday Chocolate', 'difficulty': 'Easy', 'category': 'Array'},
                {'title': 'Divisible Sum Pairs', 'difficulty': 'Easy', 'category': 'Array'},
                {'title': 'Migratory Birds', 'difficulty': 'Easy', 'category': 'Array'}
            ],
            'github': [
                {'title': 'Personal Portfolio Website', 'difficulty': 'Easy', 'category': 'Web Development'},
                {'title': 'REST API with Flask', 'difficulty': 'Medium', 'category': 'Backend'},
                {'title': 'React Todo Application', 'difficulty': 'Medium', 'category': 'Frontend'},
                {'title': 'Machine Learning Model', 'difficulty': 'Hard', 'category': 'Data Science'},
                {'title': 'Mobile App with React Native', 'difficulty': 'Hard', 'category': 'Mobile'},
                {'title': 'DevOps Pipeline Setup', 'difficulty': 'Hard', 'category': 'DevOps'},
                {'title': 'Open Source Contribution', 'difficulty': 'Medium', 'category': 'Open Source'},
                {'title': 'Algorithm Visualizer', 'difficulty': 'Medium', 'category': 'Frontend'},
                {'title': 'Database Design Project', 'difficulty': 'Medium', 'category': 'Database'},
                {'title': 'Microservices Architecture', 'difficulty': 'Hard', 'category': 'System Design'}
            ]
        }
        
        platform_problems = sample_problems.get(platform, [])
        for problem_data in platform_problems:
            existing = Problem.query.filter_by(
                title=problem_data['title'], 
                platform=platform
            ).first()
            
            if not existing:
                problem = Problem()
                problem.title = problem_data['title']
                problem.platform = platform
                problem.difficulty = problem_data['difficulty']
                problem.category = problem_data['category']
                problem.url = f"https://{platform}.com/problems/{problem_data['title'].lower().replace(' ', '-')}"
                problem.description = f"Practice problem: {problem_data['title']} - {problem_data['category']}"
                db.session.add(problem)
        
        db.session.commit()
    
    def get_platform_progress(self, user_id):
        """Get comprehensive progress across all platforms"""
        stats = PlatformStats.query.filter_by(user_id=user_id).all()
        
        progress = {
            'total_problems': 0,
            'total_easy': 0,
            'total_medium': 0,
            'total_hard': 0,
            'platforms': {}
        }
        
        for stat in stats:
            progress['total_problems'] += stat.total_problems
            progress['total_easy'] += stat.easy_solved
            progress['total_medium'] += stat.medium_solved
            progress['total_hard'] += stat.hard_solved
            
            progress['platforms'][stat.platform] = {
                'name': self.platforms[stat.platform]['name'],
                'color': self.platforms[stat.platform]['color'],
                'total': stat.total_problems,
                'easy': stat.easy_solved,
                'medium': stat.medium_solved,
                'hard': stat.hard_solved,
                'rating': stat.contest_rating,
                'streak': stat.streak,
                'last_updated': stat.last_updated
            }
        
        return progress
    
    def get_recent_activity(self, user_id, days=7):
        """Get recent coding activity"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_problems = ProblemSolved.query.filter(
            ProblemSolved.user_id == user_id,
            ProblemSolved.solved_at >= cutoff_date
        ).order_by(ProblemSolved.solved_at.desc()).all()
        
        return recent_problems
    
    def get_weak_areas(self, user_id):
        """Identify areas where user needs improvement"""
        problems_solved = ProblemSolved.query.filter_by(user_id=user_id).all()
        
        if not problems_solved:
            return []
        
        # Analyze performance by category
        category_stats = {}
        for solution in problems_solved:
            if solution.problem and solution.problem.category:
                category = solution.problem.category
                if category not in category_stats:
                    category_stats[category] = {
                        'total': 0,
                        'avg_time': 0,
                        'avg_rating': 0,
                        'difficulties': {'Easy': 0, 'Medium': 0, 'Hard': 0}
                    }
                
                category_stats[category]['total'] += 1
                if solution.time_taken:
                    category_stats[category]['avg_time'] += solution.time_taken
                if solution.personal_rating:
                    category_stats[category]['avg_rating'] += solution.personal_rating
                if solution.problem.difficulty:
                    category_stats[category]['difficulties'][solution.problem.difficulty] += 1
        
        # Calculate averages and identify weak areas
        weak_areas = []
        for category, stats in category_stats.items():
            if stats['total'] > 0:
                avg_time = stats['avg_time'] / stats['total']
                avg_rating = stats['avg_rating'] / stats['total'] if stats['avg_rating'] > 0 else 0
                
                # Consider an area weak if low rating or high average time
                if avg_rating < 3 or avg_time > 60:  # 60 minutes threshold
                    weak_areas.append({
                        'category': category,
                        'problems_solved': stats['total'],
                        'avg_time': avg_time,
                        'avg_rating': avg_rating,
                        'reason': 'Low rating' if avg_rating < 3 else 'High average time'
                    })
        
        return weak_areas
