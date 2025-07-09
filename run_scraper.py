import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Credentials
USERNAME = os.environ.get('SATU_USER')
PASSWORD = os.environ.get('SATU_PASS')

if not USERNAME or not PASSWORD:
    print("FATAL: SATU_USER or SATU_PASS secrets not set.")
    exit(1)

# URLs
LOGIN_URL = "https://www.sat-universe.com/index.php?login/login"
THREAD_URLS = [
    "https://www.sat-universe.com/index.php?threads/greece-cyprus-north-macedonia-football-feeds-10%C2%B0e-7%C2%B0e-15%C2%B0w-0-8%C2%B0w-etc.274535/",
    "https://www.sat-universe.com/index.php?threads/basketball-cba-wcba-lnb-tbl-euroleague-nba-feeds-7%C2%B0e-10%C2%B0e-16%C2%B0e-62%C2%B0e-100-5%C2%B0e-110-5%C2%B0e.259695/",
    "https://www.sat-universe.com/index.php?threads/uefa-champions-league-europa-league-super-cup-u16-u17-u19-u21-etc-3-1%C2%B0e-7%C2%B0e-10%C2%B0e-16%C2%B0e-8%C2%B0w-0-8%C2%B0w.242891/",
    "https://www.sat-universe.com/index.php?threads/wrestling-wwe-tna-aew-impact-wosw-all-brands-all-events-keys-only-plz-no-chat-use-encryption-chat-for-chat.278606/"
]
FEEDS_FILE = "feeds.txt"
PAGES_TO_SCRAPE = 2

def main():
    print(f"Smart Scraping process started. Will check last {PAGES_TO_SCRAPE} pages for today's posts...")
    
    today_str = datetime.utcnow().strftime('%b %d, %Y')
    print(f"Today's date (UTC): {today_str}")
    
    todays_posts = []

    with requests.Session() as session:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
        })
        
        # LOGIN
        try:
            print("Attempting to login...")
            login_page = session.get(LOGIN_URL)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            token = soup.find('input', {'name': '_xfToken'})['value']
            login_payload = {
                'login': USERNAME, 'password': PASSWORD, 'remember': '1', '_xfToken': token
            }
            post_login = session.post(LOGIN_URL, data=login_payload)
            if 'login/login' in post_login.url or "incorrect_password" in post_login.text:
                print("FATAL: Login failed.")
                exit(1)
            print("Login successful.")
        except Exception as e:
            print(f"Login process failed: {e}")
            exit(1)

        # ΕΠΕΞΕΡΓΑΣΙΑ ΚΑΘΕ THREAD
        for thread_url in THREAD_URLS:
            try:
                print("\n" + "="*50)
                print(f"Processing thread: {thread_url.split('/')[-2][:50]}...") # Συντομευμένο όνομα
                main_thread_page = session.get(thread_url)
                soup = BeautifulSoup(main_thread_page.text, 'html.parser')
                
                last_page_num = 1
                page_nav = soup.find('ul', class_='pageNav-main')
                if page_nav:
                    last_page_link = page_nav.find_all('li')[-1].a
                    if last_page_link and last_page_link.text.isdigit():
                        last_page_num = int(last_page_link.text)
                print(f"Thread has {last_page_num} pages.")

                start_page = max(1, last_page_num - PAGES_TO_SCRAPE + 1)
                
                for page_num in range(last_page_num, start_page - 1, -1):
                    page_url = f"{thread_url}page-{page_num}"
                    print(f"  Scraping page {page_num}...")
                    
                    page_content = session.get(page_url)
                    page_soup = BeautifulSoup(page_content.text, 'html.parser')
                    posts = page_soup.find_all('article', class_='message')

                    for post in posts:
                        date_element = post.find('time', class_='u-dt')
                        if not date_element: continue
                        
                        post_date_str = date_element.get_text(strip=True)
                        
                        # --- Η ΔΙΟΡΘΩΣΗ ΕΙΝΑΙ ΕΔΩ ---
                        # Ελέγχουμε αν η ημερομηνία είναι "Today", "minutes ago", "hour ago" ή ταιριάζει με τη σημερινή
                        is_today = False
                        if "Today" in post_date_str or "minutes ago" in post_date_str or "hour ago" in post_date_str or "Just now" in post_date_str or today_str in post_date_str:
                             is_today = True
                        
                        if is_today:
                            wrapper = post.find('div', class_='bbWrapper')
                            if wrapper:
                                post_text = wrapper.get_text(separator='\n', strip=True)
                                if post_text not in todays_posts:
                                    print(f"    + Found a post from '{post_date_str}'")
                                    todays_posts.append(post_text)
                        # ---------------------------

            except Exception as e:
                print(f"!!! Failed during scraping for thread {thread_url}: {e}")
                continue
        
        print("="*50)

    # Αντικαθιστούμε το αρχείο ΜΟΝΟ με τα σημερινά posts
    if todays_posts:
        todays_posts.reverse()
        with open(FEEDS_FILE, 'w', encoding='utf-8') as f:
            separator = "\n---FEED-SEPARATOR---\n"
            f.write(separator.join(todays_posts))
        print(f"Successfully wrote {len(todays_posts)} posts from today to {FEEDS_FILE}.")
    else:
        open(FEEDS_FILE, 'w').close()
        print("No posts from today were found. feeds.txt is now empty.")

if __name__ == '__main__':
    main()
