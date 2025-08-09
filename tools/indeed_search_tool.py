import requests
from bs4 import BeautifulSoup


def search_indeed_jobs(role: str, location: str) -> list[dict]:
    """Searches for jobs on Indeed."""
    print(f"INFO: Searching Indeed for '{role}' in '{location}'...")
    url = f"https://in.indeed.com/jobs?q={role.replace(' ', '+')}&l={location.replace(' ', '+')}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Indeed uses a specific script tag to hold job data often
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        jobs = []
        for card in job_cards:
            title_element = card.find('h2', class_='jobTitle').find('a') if card.find('h2', class_='jobTitle') else None
            company_element = card.find('span', class_='companyName')

            if all([title_element, company_element]):
                job_url = "https://in.indeed.com" + title_element['href']
                jobs.append({
                    "platform": "Indeed",
                    "title": title_element.text.strip(),
                    "company": company_element.text.strip(),
                    "url": job_url
                })
        print(f"INFO: Found {len(jobs)} jobs on Indeed.")
        return jobs
    except Exception as e:
        print(f"ERROR (Indeed): {e}")
        return []