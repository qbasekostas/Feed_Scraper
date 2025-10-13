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
    "https://www.sat-universe.com/index.php?threads/greece-football-fta.311066/",
    "https://www.sat-universe.com/index.php?threads/basketball-cba-wcba-lnb-tbl-euroleague-nba-feeds-7%C2%B0e-10%C2%B0e-16%C2%B0e-62%C2%B0e-100-5%C2%B0e-110-5%C2%B0e.259695/",
    "https://www.sat-universe.com/index.php?threads/basketball-fta-feeds.298604/",
    "https://www.sat-universe.com/index.php?threads/uefa-champions-league-europa-league-super-cup-u16-u17-u19-u21-etc-3-1%C2%B0e-7%C2%B0e-10%C2%B0e-16%C2%B0e-8%C2%B0w-0-8%C2%B0w.242891/",
    "https://www.sat-universe.com/index.php?threads/uefa-champions-europa-league-conference-league-feeds.150085/",
    "https://www.sat-universe.com/index.php?threads/uefa-international-football-euro-qualifiers-friendlies-preseason-continental-cup-hybrid-legends-etc-please-state-if-4-2-0-or-4-2-2.276471/",
    "https://www.sat-universe.com/index.php?threads/fifa-internationals-fifa-world-cup-2014-2018-2022-2026-qualifiers-friendlies-world-club-championship-7%C2%B0e-10%C2%B0e-etc.240056/",
    "https://www.sat-universe.com/index.php?threads/fifa-uefa-international-football-euro-qualifiers-world-cup-qualifiers-friendlies-c-ku-please-state-if-4-2-0-or-4-2-2.276471/",
    "https://www.sat-universe.com/index.php?threads/fifa-inter-football-hybrid-club-not-for-club-vs-club-from-same-country-spain-england-portugal-etc-have-there-own-threads.277750/",
    "https://www.sat-universe.com/index.php?threads/english-scotish-welsh-irish-football-please-state-if-420-or-422-28-2%C2%B0e-23-5%C2%B0e-10%C2%B0e-7%C2%B0e-100-5%C2%B0e-0-8%C2%B0west.252475/",
    "https://www.sat-universe.com/index.php?threads/uk-eng-scot-wales-ire-premier-lge-championship-sheild-fa-cup-friendlies-league-cup-3-1%C2%B0e-7%C2%B0e-10%C2%B0e-100-5%C2%B0e.265788/",
    "https://www.sat-universe.com/index.php?threads/spain-football-please-include-4-2-0-or-4-2-2-info-in-your-post.249958/",
    "https://www.sat-universe.com/index.php?threads/italy-football-if-4-2-2-or-4-2-0-please-include-this-info-in-your-post.252376/",
    "https://www.sat-universe.com/index.php?threads/south-american-football-argentina-brazil-paraguay-chile-inc-conmebol-copa-am%C3%A9rica.251795/",
    "https://www.sat-universe.com/index.php?threads/german-football-bundesliga-etc-if-4-2-2-or-4-2-0-please-include-this-info-in-your-post.253481/"
    ]
FEEDS_FILE = "feeds.txt"
PAGES_TO_SCRAPE = 2


# --- ΣΥΝΑΡΤΗΣΗ ΓΙΑ ΤΗ ΔΙΟΡΘΩΣΗ (ΕΝΗΜΕΡΩΜΕΝΗ ΛΟΓΙΚΗ) ---
def format_post_text(post_text):
    """
    Διορθώνει και ενοποιεί τη μορφοποίηση του κειμένου ενός post.
    1. Διορθώνει τις "σπασμένες" γραμμές πόλωσης.
    2. Τυποποιεί τις λέξεις 'HORIZONTAL'/'VERTICAL' στα γράμματα 'H'/'V'.
    """
    lines = post_text.splitlines()
    processed_lines = []
    i = 0
    while i < len(lines):
        current_line = lines[i].strip()

        # --- ΚΑΝΟΝΑΣ 1: Ένωση "σπασμένων" γραμμών ---
        if i + 2 < len(lines):
            freq_line = current_line
            pol_char_line = lines[i+1].strip()
            rest_of_params_line = lines[i+2].strip()

            if freq_line.isdigit() and pol_char_line.upper() == 'H' and rest_of_params_line.lower().startswith('orizontal'):
                params = rest_of_params_line[len('orizontal'):].strip()
                new_line = f"{freq_line} H {params}"
                processed_lines.append(new_line)
                i += 3
                continue

            if freq_line.isdigit() and pol_char_line.upper() == 'V' and rest_of_params_line.lower().startswith('ertical'):
                params = rest_of_params_line[len('ertical'):].strip()
                new_line = f"{freq_line} V {params}"
                processed_lines.append(new_line)
                i += 3
                continue
        
        # --- ΝΕΟΣ ΚΑΝΟΝΑΣ 2: Τυποποίηση λέξεων (π.χ. 'VERTICAL' -> 'V') ---
        parts = current_line.split()
        # Ελέγχουμε αν η γραμμή έχει τη μορφή: Αριθμός Λέξη Αριθμός... (π.χ. 10965 VERTICAL 14400)
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isalpha() and parts[2].isdigit():
            if parts[1].upper() == 'VERTICAL':
                parts[1] = 'V'
                processed_lines.append(" ".join(parts))
                i += 1
                continue
            elif parts[1].upper() == 'HORIZONTAL':
                parts[1] = 'H'
                processed_lines.append(" ".join(parts))
                i += 1
                continue

        # --- ΚΑΝΟΝΑΣ 3: Επεξεργασία CW ---
        temp_line = current_line.upper().replace("#", "").replace(":", "").strip()
        if temp_line == 'CW':
            if i + 1 < len(lines):
                key = lines[i+1].strip()
                if ' ' in key and len(key) > 10:
                    processed_lines.append(f"CW: {key}")
                    i += 2
                    continue
        
        if current_line.upper().lstrip().startswith('#CW:') or current_line.upper().lstrip().startswith('CW:'):
            key_part = current_line.split(':', 1)
            if len(key_part) > 1 and key_part[1].strip():
                processed_lines.append(f"CW: {key_part[1].strip()}")
                i += 1
                continue

        # Αν δεν ταιριάζει κανένας κανόνας, προσθέτει την τρέχουσα γραμμή ως έχει
        processed_lines.append(lines[i])
        i += 1

    return "\n".join(filter(str.strip, processed_lines))
# -----------------------------------------------------------


def main():
    print(f"Smart Scraping process started. Will check last {PAGES_TO_SCRAPE} pages for today's posts...")
    
    today_str = datetime.utcnow().strftime('%b %d, %Y')
    print(f"Today's date (UTC): {today_str}")
    
    todays_posts = []

    with requests.Session() as session:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
        })
        
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

        for thread_url in THREAD_URLS:
            try:
                print("\n" + "="*50)
                print(f"Processing thread: {thread_url.split('/')[-2][:50]}...")
                main_thread_page = session.get(thread_url)
                soup = BeautifulSoup(main_thread_page.text, 'html.parser')
                
                last_page_num = 1
                page_nav = soup.find('ul', class_='pageNav-main')
                if page_nav:
                    last_page_links = page_nav.find_all('li')
                    if last_page_links:
                        last_page_text = last_page_links[-1].get_text(strip=True)
                        if last_page_text.isdigit():
                            last_page_num = int(last_page_text)
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
                        
                        is_today = False
                        if "Today" in post_date_str or "minutes ago" in post_date_str or "hour ago" in post_date_str or "Just now" in post_date_str or today_str in post_date_str:
                             is_today = True
                        
                        if is_today:
                            wrapper = post.find('div', class_='bbWrapper')
                            if wrapper:
                                original_post_text = wrapper.get_text(separator='\n', strip=False)
                                corrected_post_text = format_post_text(original_post_text)
                                
                                if corrected_post_text and corrected_post_text not in todays_posts:
                                    print(f"    + Found a post from '{post_date_str}'")
                                    todays_posts.append(corrected_post_text)

            except Exception as e:
                print(f"!!! Failed during scraping for thread {thread_url}: {e}")
                continue
        
        print("="*50)

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
