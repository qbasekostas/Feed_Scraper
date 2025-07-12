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
    "https://www.sat-universe.com/index.php?threads/uefa-international-football-euro-qualifiers-friendlies-preseason-continental-cup-hybrid-legends-etc-please-state-if-4-2-0-or-4-2-2.276471/",
    "https://www.sat-universe.com/index.php?threads/fifa-internationals-fifa-world-cup-2014-2018-2022-2026-qualifiers-friendlies-world-club-championship-7%C2%B0e-10%C2%B0e-etc.240056/",
    "https://www.sat-universe.com/index.php?threads/basketball-fta-feeds.298604/",
    "https://www.sat-universe.com/index.php?threads/greece-football-fta.311066/",
    "https://www.sat-universe.com/index.php?threads/english-scotish-welsh-irish-football-please-state-if-420-or-422-28-2%C2%B0e-23-5%C2%B0e-10%C2%B0e-7%C2%B0e-100-5%C2%B0e-0-8%C2%B0west.252475/",
    "https://www.sat-universe.com/index.php?threads/fifa-uefa-international-football-euro-qualifiers-world-cup-qualifiers-friendlies-c-ku-please-state-if-4-2-0-or-4-2-2.276471/"
]
FEEDS_FILE = "feeds.txt"
PAGES_TO_SCRAPE = 2


# --- ΣΥΝΑΡΤΗΣΗ ΓΙΑ ΤΗ ΔΙΟΡΘΩΣΗ (ΕΝΗΜΕΡΩΜΕΝΗ ΛΟΓΙΚΗ) ---
def format_post_text(post_text):
    """
    Διορθώνει και ενοποιεί τη μορφοποίηση του κειμένου ενός post.
    Ειδικα, διορθώνει τις λανθασμενα "σπασμενες" γραμμες πολωσης.
    """
    lines = post_text.splitlines()
    processed_lines = []
    i = 0
    while i < len(lines):
        # Τρίβουμε τα κενά από την αρχή και το τέλος για ασφαλείς ελέγχους
        current_line = lines[i].strip()

        # --- ΝΕΑ ΛΟΓΙΚΗ: Ελεγχος για τη "σπασμένη" γραμμή πόλωσης ---
        # Ελέγχουμε αν έχουμε μπροστά μας τουλάχιστον 3 γραμμές
        if i + 2 < len(lines):
            # Παίρνουμε τις τρεις υποψήφιες γραμμές
            freq_line = current_line
            pol_char_line = lines[i+1].strip()
            rest_of_params_line = lines[i+2].strip()

            # ΠΕΡΙΠΤΩΣΗ 1: HORIZONTAL
            # Ελέγχουμε αν το μοτίβο είναι: Αριθμός -> "H" -> "orizontal ..."
            if freq_line.isdigit() and pol_char_line.upper() == 'H' and rest_of_params_line.lower().startswith('orizontal'):
                # Παίρνουμε το υπόλοιπο της τρίτης γραμμής, αφαιρώντας το λανθασμένο "orizontal"
                params = rest_of_params_line[len('orizontal'):].strip()
                # Συνθέτουμε τη νέα, διορθωμένη γραμμή
                new_line = f"{freq_line} H {params}"
                processed_lines.append(new_line)
                # Αυξάνουμε τον δείκτη κατά 3 για να προσπεράσουμε τις 3 γραμμές που επεξεργαστήκαμε
                i += 3
                continue

            # ΠΕΡΙΠΤΩΣΗ 2: VERTICAL
            # Ελέγχουμε αν το μοτίβο είναι: Αριθμός -> "V" -> "ertical ..."
            if freq_line.isdigit() and pol_char_line.upper() == 'V' and rest_of_params_line.lower().startswith('ertical'):
                params = rest_of_params_line[len('ertical'):].strip()
                new_line = f"{freq_line} V {params}"
                processed_lines.append(new_line)
                i += 3
                continue
        
        # --- ΥΠΑΡΧΟΥΣΑ ΛΟΓΙΚΗ ΓΙΑ ΤΟ CW (παραμένει ως έχει) ---
        # Αν δεν βρέθηκε το παραπάνω μοτίβο, συνεχίζουμε με τους υπόλοιπους ελέγχους
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

        # Αν δεν ταιριάζει κανένας ειδικός κανόνας, προσθέτει την τρέχουσα γραμμή ως έχει
        # (Χρησιμοποιούμε την αρχική γραμμή από τη λίστα για να διατηρηθούν τυχόν αρχικά κενά αν χρειάζεται)
        processed_lines.append(lines[i])
        i += 1

    # Ενώνουμε τις γραμμές, φιλτράροντας τυχόν εντελώς κενές γραμμές
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
