import requests
from bs4 import BeautifulSoup
import time
import re

def extract_search_results(soup):
    # Find the list of movies or series based on search
    search_list = soup.find('ul', class_='recent-movies')
    if not search_list:
        return []
    
    results = []
    
    # Find all list items
    search_items = search_list.find_all('li', class_='thumb')
    
    for idx, item in enumerate(search_items, 1):
        try:
            # Extract image info
            img = item.find('img')
            thumbnail = img['src'] if img else "No thumbnail"
            
            # Extract link and title
            link_elem = item.find('a')
            if link_elem:
                link = link_elem['href']
                # Find the title in the paragraph tag
                title = item.find('p').text.strip() if item.find('p') else "No title"
                
                results.append({
                    'id': idx,
                    'title': title,
                    'link': link,
                    'thumbnail': thumbnail
                })
        except Exception as e:
            print(f"Error processing search item: {e}")
            continue
    
    return results

def search_movies_or_series(query):
    base_url = "https://moviesdrive.pro/"
    search_url = f"{base_url}?s={query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Searching for: {query}")
        print("Please wait...")
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        search_results = extract_search_results(soup)
        
        if not search_results:
            print("No results found!")
            return None
        
        # Print search results
        print("\nSearch Results:")
        print("-" * 50)
        
        for result in search_results:
            print(f"\n{result['id']}. {result['title']}")
            print(f"   Link: {result['link']}")
            print(f"   Thumbnail: {result['thumbnail']}")
            print("-" * 50)
        
        return search_results, headers
        
    except requests.RequestException as e:
        print(f"Error fetching the results: {e}")
        return None

def get_movies_links(main_body):
    download_links = []
     # Find all h5 tags with download links
    h5_tags = main_body.find_all('h5', style='text-align: center;')
    
    for i in range(0, len(h5_tags), 2):  # Step by 2 since links come in pairs
        if i + 1 < len(h5_tags):  # Make sure we have both title and link
            title_tag = h5_tags[i]
            link_tag = h5_tags[i + 1].find('a')
            
            if title_tag and link_tag:
                # Extract the quality info from the title
                quality_span = title_tag.find('span', style='color: #00ff00;')
                if quality_span:
                    title = quality_span.text.strip()
                    link = link_tag['href']
                    
                    download_links.append({
                        'title': title,
                        'link': link
                    })
    
    return download_links

def get_series_links(main_body):
    h5_tags = main_body.find_all('h5', style='text-align: center;')
    download_links = {}
    current_title = ""

    for tag in h5_tags:
        span_tag = tag.find('span', style='color: #ff0000;')
        if span_tag:
            current_title = tag.get_text(strip=True)
            if current_title not in download_links:
                download_links[current_title] = []
        else:
            link_tag = tag.find('a')
            if link_tag and current_title:
                download_links[current_title].append({
                    'link_text': link_tag.get_text(strip=True),
                    'link': link_tag['href']
                })
    return download_links

def get_item_info_and_links(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        info = {}
        
        main_body = soup.find('main', class_='page-body')
        first_h3_tag = main_body.find('h3')
        item_type = first_h3_tag.get_text()
        
        is_movie = False
        
        if item_type == 'Movie Info:':
            is_movie = True
            # Extract movie title and year from title tag
            if title_tag := soup.find('title'):
                title_text = title_tag.text
                
                # Extract movie name and year using regex
                if movie_match := re.search(r'(.*?)\s*\((\d{4})\)', title_text):
                    info['Movie Name'] = movie_match.group(1).strip()
                    info['Released Year'] = movie_match.group(2)
                
                # Extract language
                if '[' in title_text and ']' in title_text:
                    info['Language'] = title_text.split('[')[1].split(']')[0].strip()
            
            # Extract IMDb rating
            if inner_main_div := soup.find('div', class_='yQ8hqd ksSzJd w6Utff'):
                if inner_div := inner_main_div.find('div', class_='NFQFxe CQKTwc mod'):
                    if rating_link := inner_main_div.find('a'):
                        if rating_text := rating_link.text:
                            info['IMDb Rating'] = rating_text.strip()

            # Extract genre from meta description
            if meta_desc := soup.find('meta', {'name': 'description'}):
                if desc_text := meta_desc.get('content', ''):
                    if genre_match := re.search(r'based on (.*?),', desc_text):
                        info['Genre'] = genre_match.group(1).strip()
            
            return info, get_movies_links(main_body), is_movie
        
        else:
            # Find the info paragraph with all the details
            if info_p := first_h3_tag.find_next('p'):
                # Extract IMDb rating
                if imdb_link := info_p.find('a', href=lambda x: x and 'imdb.com' in x):
                    info['IMDb Rating'] = imdb_link.text.replace('👉 IMDb Rating:- ', '')
                
                # Extract other information using the text content
                for strong in info_p.find_all('strong'):
                    label = strong.text.strip(':')
                    if label == 'Series Name':
                        info['Series Name'] = strong.find_next('span').text.strip()
                    elif label in ['Season', 'Episode', 'Language']:
                        next_element = strong.find_next('span') or strong.next_sibling
                        info[label] = next_element.text.strip()
                        
            return info, get_series_links(main_body), is_movie
        
    except Exception as e:
        print(f"Error fetching movie/series details: {e}")
        return None

def display_movie_details(info, download_links):
    if not info or not download_links:
        print("No details available!")
        return
        
    print("\nMovie Details:")
    print("-" * 50)
    for key, value in info.items():
        print(f"{key}: {value}")
    print("\nDownload Links:")
    print("-" * 50)
    
    # Store all links for easy selection
    all_links = []
    
    for idx, link in enumerate(download_links, 1):
        all_links.append(link)
        print(f"    {idx}. {link['title']}")
        print(f"       {link['link']}")
    print("-" * 50)

    # Ask user to select a link
    while True:
        selection = input("\nEnter the number of the link you want to download (or 'b' to return): ").strip()
        
        if selection.lower() == 'b':
            return None
            
        try:
            selection_idx = int(selection)
            if 1 <= selection_idx <= len(all_links):
                selected_link = all_links[selection_idx - 1]
                print(f"\nYou selected:")
                print(f"Quality: {selected_link['title']}")
                print(f"Link: {selected_link['link']}")
                print(f"Getting final download link...")
                return selected_link
            else:
                print("Invalid selection! Please enter a valid number.")
        except ValueError:
            print("Please enter a valid number!")

def display_series_details(info, download_links, headers):
    if not info or not download_links:
        print("No episode links available!")
        return
    
    print("\nSeries Details:")
    print("-" * 50)
    for key, value in info.items():
        print(f"{key}: {value}")
    print("\nDownload Links:")
    print("-" * 50)
    
    # Store all links for easy selection
    all_links = []
    
    # Print available download links
    for i, (title, links) in enumerate(download_links.items(), 1):
        print(f"{i}. {title}")
        for link_info in links:
            all_links.append({
                'title': title,
                'link_text': link_info['link_text'],
                'link': link_info['link']
            })
            print(f"   - {link_info['link_text']}: {link_info['link']}")
        print("-" * 30)
    
    # Ask user to select a link
    while True:
        selection = input("\nEnter the number of the quality you want to download (or 'b' to return): ").strip()
        
        if selection.lower() == 'b':
            return None
            
        try:
            selection_idx = int(selection)
            titles = list(download_links.keys())
            
            if 1 <= selection_idx <= len(titles):
                selected_title = titles[selection_idx - 1]
                selected_links = download_links[selected_title]
                
                print(f"\nYou selected: {selected_title}")
                print("\nAvailable download options:")
                for i, link_info in enumerate(selected_links, 1):
                    print(f"{i}. {link_info['link_text']}")
                
                while True:
                    option = input("\nEnter option number (or 'b' to go back): ").strip()
                    
                    if option.lower() == 'b':
                        break
                        
                    try:
                        option_idx = int(option)
                        if 1 <= option_idx <= len(selected_links):
                            selected_link = selected_links[option_idx - 1]['link']
                            print("\nGetting episode links...")
                            
                            episodes, zipped_episodes = get_all_episodes_links(selected_link, headers)
                            if episodes or zipped_episodes:
                                if episodes:
                                    print("\nAvailable Episodes:")
                                    for i, episode in enumerate(episodes, 1):
                                        print(f"\n{i}. Episode: {episode['episode']}")
                                        if episode['size']:
                                            print(f"   Size: {episode['size']}")
                                        if episode['hubcloud']:
                                            print(f"   HubCloud: {episode['hubcloud']}")
                                        if episode['gdflix']:
                                            print(f"   GDFlix Link: {episode['gdflix']}")
                                
                                    while True:
                                        episode_choice = input("\nEnter number to download (or 'b' to go back): ").strip()
                                        
                                        if episode_choice.lower() == 'b':
                                            break
                                            
                                        try:
                                            episode_idx = int(episode_choice)
                                            if 1 <= episode_idx <= len(episodes):
                                                selected_episode = episodes[episode_idx - 1]
                                                
                                                if selected_episode['hubcloud']:
                                                    print("\nGetting download link...")
                                                    final_url = get_hubcloud_download_link_for_episode(selected_episode['hubcloud'], headers)
                                                    if final_url:
                                                        print(f"\nDownload Link for {selected_episode['episode']}:")
                                                    else:
                                                        print("Could not get download link")
                                                else:
                                                    print("No HubCloud link available for this item")
                                                return None
                                            else:
                                                print("Invalid number! Please try again.")
                                        except ValueError:
                                            print("Please enter a valid number!")
                                            
                                elif zipped_episodes:
                                    print("\nAvailable Zipped Episodes:")
                                    for i, episode in enumerate(zipped_episodes, 1):
                                        print(f"\n{i}. {episode['season']}")
                                        if episode['size']:
                                            print(f"   Size: {episode['size']}")
                                        if episode['hubcloud']:
                                            print(f"   HubCloud: {episode['hubcloud']}")
                                        if episode['gdflix']:
                                            print(f"   GDFlix Link: {episode['gdflix']}")
                                    
                                    while True:
                                        episode_choice = input("\nEnter number to download (or 'b' to go back): ").strip()
                                        
                                        if episode_choice.lower() == 'b':
                                            break
                                            
                                        try:
                                            episode_idx = int(episode_choice)
                                            if 1 <= episode_idx <= len(zipped_episodes):
                                                selected_episode = zipped_episodes[episode_idx - 1]
                                                
                                                if selected_episode['hubcloud']:
                                                    print("\nGetting download link...")
                                                    final_url = get_hubcloud_download_link_for_episode(selected_episode['hubcloud'], headers)
                                                    if final_url:
                                                        print(f"\nDownload Link for {selected_episode['season']}:")
                                                    else:
                                                        print("Could not get download link")
                                                else:
                                                    print("No HubCloud link available for this item")
                                                return None
                                            else:
                                                print("Invalid number! Please try again.")
                                        except ValueError:
                                            print("Please enter a valid number!")
                            else:
                                print("Could not get any episode links")
                                return None
                        else:
                            print("Invalid option! Please enter a valid number.")
                    except ValueError:
                        print("Please enter a valid number!")
            else:
                print("Invalid selection! Please enter a valid number.")
        except ValueError:
            print("Please enter a valid number!")

def get_all_episodes_links(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        episodes = []
        zipped_episodes = []
        
        # Find all episode sections
        episode_sections = soup.find_all('h5', style='text-align: center;')
        for section in episode_sections:
            # Look for episode numbers
            episode_text = section.find('span', style='color: #ff0000;')
            if episode_text and episode_text.text.startswith('Ep'):
                episode_num = episode_text.text
                
                # Get file size if available
                size_text = section.find('span', style='color: #0000ff;')
                size = size_text.text if size_text else None
                
                # Get links with null checks
                next_h5 = section.find_next('h5')
                next_next_h5 = next_h5.find_next('h5') if next_h5 else None
                
                hubcloud_link = None
                gdflix_link = None
                
                if next_h5 and next_h5.find('a'):
                    hubcloud_link = next_h5.find('a').get('href')
                if next_next_h5 and next_next_h5.find('a'):
                    gdflix_link = next_next_h5.find('a').get('href')
                
                if hubcloud_link or gdflix_link:
                    episodes.append({
                        'episode': episode_num,
                        'size': size,
                        'hubcloud': hubcloud_link,
                        'gdflix': gdflix_link
                    })
            else:
                # Handle season/complete series entries
                season_text = section.find('span', style='color: #ff0000;')
                if season_text and 'Season' in season_text.text:
                    size_text = section.find('span', style='color: #0000ff;')
                    size = size_text.text if size_text else None
                    
                    # Get links with null checks
                    next_h5 = section.find_next('h5')
                    next_next_h5 = next_h5.find_next('h5') if next_h5 else None
                    next_next_next_h5 = next_next_h5.find_next('h5') if next_next_h5 else None
                    
                    hubcloud_link = None
                    gdflix_link = None
                    gdtot_link = None
                    
                    if next_h5 and next_h5.find('a'):
                        hubcloud_link = next_h5.find('a').get('href')
                    if next_next_h5 and next_next_h5.find('a'):
                        gdflix_link = next_next_h5.find('a').get('href')
                    if next_next_next_h5 and next_next_next_h5.find('a'):
                        gdtot_link = next_next_next_h5.find('a').get('href')
                    
                    if hubcloud_link or gdflix_link or gdtot_link:
                        zipped_episodes.append({
                            'type': 'season',
                            'season': season_text.text,
                            'size': size,
                            'hubcloud': hubcloud_link,
                            'gdflix': gdflix_link,
                            'gdtot': gdtot_link
                        })
                        
        return episodes, zipped_episodes
    except Exception as e:
        print(f"Error getting episode links: {str(e)}")
        return [], []  # Return empty lists instead of single None

def get_hubcloud_download_link(url, headers):
    try:
        # First page with the "Generate Direct Download Link" button
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Get the hubcloud.ink URL
        hubcloud_url = None
        hubcloud_link = soup.find('a', href=lambda x: x and 'hubcloud.ink' in x)
        if hubcloud_link:
            hubcloud_url = hubcloud_link['href']
        
        if not hubcloud_url:
            print("Could not find hubcloud URL")
            return None
            
        # Get the second page with the final download link
        print(hubcloud_url)
        response = requests.get(hubcloud_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get the redirect URL from the meta refresh tag
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh:
            content = meta_refresh.get('content', '')
            url = content.split('url=')[1] if 'url=' in content else None
            print(f"Redirect URL: {url}")
        
        
        
        # Extract the final download URL from the script
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'shetkaritoday.in' in script.string:
                start = script.string.find("url = '") + 7
                end = script.string.find("'", start)
                if start > 7:
                    final_url = script.string[start:end]
                    # Fetch and parse the final URL
                    final_response = requests.get(final_url, headers=headers)
                    final_soup = BeautifulSoup(final_response.content, 'html.parser')
                    card_body = final_soup.find('div', class_='card-body')
                    # Find all download buttons
                    download_links = {}
                    download_buttons = card_body.find_all('a', class_='btn')
                    
                    for button in download_buttons:
                        if button.get('href'):
                            download_links[button.text.strip()] = button['href']
                    
                    print("\nAvailable Download Links:")
                    print("-" * 50)
                    for title, link in download_links.items():
                        print(f"{title}: {link}")
                    
                    return download_links
        
        print("Could not find final download URL")
        return None
            
    except Exception as e:
        print(f"Error getting final download link: {e}")
        return None

def get_hubcloud_download_link_for_episode(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
         # Get the redirect URL from the meta refresh tag
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh:
            content = meta_refresh.get('content', '')
            url = content.split('url=')[1] if 'url=' in content else None
            print(f"Redirect URL: {url}")
        
        # Extract the final download URL from the script
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        div = soup.find('div', class_='vd')
        a_tag = div.find('a') if div else None
        link = a_tag.get('href') if a_tag else None
        if link:
            # Fetch and parse the final URL
            final_response = requests.get(link, headers=headers)
            final_soup = BeautifulSoup(final_response.content, 'html.parser')
            card_body = final_soup.find('div', class_='card-body')
            # Find all download buttons
            download_links = {}
            download_buttons = card_body.find_all('a', class_='btn')
            
            for button in download_buttons:
                if button.get('href'):
                    download_links[button.text.strip()] = button['href']
            
            print("\nAvailable Download Links:")
            print("-" * 50)
            for title, link in download_links.items():
                print(f"{title}: {link}")
            
            return download_links
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'shetkaritoday.in' in script.string:
                start = script.string.find("url = '") + 7
                end = script.string.find("'", start)
                if start > 7:
                    final_url = script.string[start:end]
                    # Fetch and parse the final URL
                    final_response = requests.get(final_url, headers=headers)
                    final_soup = BeautifulSoup(final_response.content, 'html.parser')
                    card_body = final_soup.find('div', class_='card-body')
                    # Find all download buttons
                    download_links = {}
                    download_buttons = card_body.find_all('a', class_='btn')
                    
                    for button in download_buttons:
                        if button.get('href'):
                            download_links[button.text.strip()] = button['href']
                    
                    print("\nAvailable Download Links:")
                    print("-" * 50)
                    for title, link in download_links.items():
                        print(f"{title}: {link}")
                    
                    return download_links
        
        print("Could not find final download URL")
        return None
        
    except Exception as e:
        print(f"Error getting final download link: {e}")
        return None
    
def main():
    while True:
        query = input("\nEnter movie/show to search (or 'q' to exit): ").strip()
        
        if query.lower() == 'q':
            print("Goodbye!")
            break
        
        if not query:
            print("Please enter a valid search term!")
            continue
        
        result = search_movies_or_series(query)
        if not result:
            continue
            
        search_results, headers = result
        
        while True:
            selection = input("\nEnter the number of the movie/show you want to view (or 'b' to search again): ").strip()
            
            if selection.lower() == 'b':
                break
                
            try:
                selection_idx = int(selection)
                if 1 <= selection_idx <= len(search_results):
                    selected_item = search_results[selection_idx - 1]
                    print(f"\nFetching details for: {selected_item['title']}")
                    print("Please wait...")
                    
                    info, download_links, is_movie = get_item_info_and_links(selected_item['link'], headers)
                    if info:
                        if is_movie:
                             # Handle movies
                            selected_link = display_movie_details(info, download_links)
                            if selected_link:
                                final_link = get_hubcloud_download_link(selected_link['link'], headers)
                                if final_link:
                                    print("\nDownload link ready!")
                            
                        else:
                            # Handle series
                            final_link = display_series_details(info, download_links, headers)
                            if final_link:
                                print("\nDownload link ready!")
                    else:
                        print("No details available!")
                    
                    break
                else:
                    print("Invalid selection! Please enter a valid number.")
            except ValueError:
                print("Please enter a valid number!")
        
        time.sleep(1)

if __name__ == "__main__":
    main()
