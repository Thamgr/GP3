#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import hashlib
import re
from PIL import Image
import io

class WildberriesParserV2:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.base_url = "https://www.wildberries.ru"

        self.create_directories()

        self.selectors = {
            'search_input': ['#searchInput', '[data-wba-header-name="SearchInput"]', 'input[placeholder*="Найти"]'],
            'product_cards': 'article[id]',
            'product_name': ['.goods-name', '.product-card__name', '[data-link] span', 'h3', '.name'],
            'product_price': ['.price__lower-price', '.lower-price', '.price', '[class*="price"]'],
            'product_image': ['img[src*="images.wbstatic"]', '.product-card__img img', 'img[alt]'],
            'product_rating': ['.product-card__rating', '[class*="rating"]', '.stars'],
            'next_page': '.pagination__next',
        }
    
    def create_directories(self):
        directories = ['images', 'data']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Created dir: {directory}")
    
    def setup_driver(self):
        chrome_options = Options()

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 15)
    
    def find_element_by_selectors(self, selectors, timeout=10):
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return element
            except TimeoutException:
                continue
        return None
    
    def search_products(self, query):
        print(f"Start search_products")
        self.driver.get(self.base_url)
        time.sleep(5)

        search_input = self.find_element_by_selectors(self.selectors['search_input'])
        
        if not search_input:
            print("No search field found")
            return

        search_input.clear()
        time.sleep(1)
        search_input.send_keys(query)
        print(f"Sent query: {query}")
        time.sleep(2)

        search_input.send_keys(Keys.RETURN)
        time.sleep(5)

        products_found = False
        selector = self.selectors['product_cards']
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            products_found = True
        except TimeoutException:
            pass
        
        if products_found:
            print("Search succeed")
        else:
            print("Search failed")
    
    def extract_text_by_selectors(self, parent_element, selectors):
        for selector in selectors:
            try:
                element = parent_element.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
                for attr in ['aria-label', 'title', 'alt']:
                    attr_text = element.get_attribute(attr)
                    if attr_text and attr_text.strip():
                        return attr_text.strip()
            except NoSuchElementException:
                continue
        return None
    
    def download_image(self, image_url, filename):
        try:
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                image_url = self.base_url + image_url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.wildberries.ru/'
            }
            
            response = requests.get(image_url, headers=headers, timeout=15)
            response.raise_for_status()

            filename_base = os.path.splitext(filename)[0]
            filename_jpg = filename_base + '.jpg'
            filepath = os.path.join('images', filename_jpg)

            image_data = io.BytesIO(response.content)
            with Image.open(image_data) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.save(filepath, 'JPEG', quality=85, optimize=True)

                file_size = os.path.getsize(filepath)
                file_size_kb = file_size / 1024
                
                print(f"Saved JPG: {filepath} ({file_size_kb:.1f} KB)")
                return filepath
        except Exception as e:
            print(f"Downloading {image_url} error: {e}")
            return None

    
    def go_to_next_page(self):
        try:
            print("Start go_to_next_page")

            current_url = self.driver.current_url

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            selector = self.selectors['next_page']
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
            
            for button in next_buttons:
                if button.is_displayed() and button.is_enabled():
                    if 'disabled' not in button.get_attribute('class').lower():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        button.click()
                        break

            print("Loading new page")
            time.sleep(5)

            new_url = self.driver.current_url
            
            if new_url == current_url:
                print("Transition fail")
                return
    
            print("go_to_next_page success")
                
        except Exception as e:
            print("go_to_next_page failed: {e}")

    
    def parse_products(self):
        products = []
        
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            product_cards = []
            selector = self.selectors['product_cards']
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    product_cards = cards
            except Exception:
                pass
            
            if not product_cards:
                return products
            
            for i, card in enumerate(product_cards):
                try:
                    product_data = {}

                    product_id = card.get_attribute("data-nm-id") or card.get_attribute("id") or f"product_{i+1}"
                    product_data['id'] = product_id

                    name = self.extract_text_by_selectors(card, self.selectors['product_name'])
                    product_data['name'] = name or f"Товар {product_id}"

                    price = self.extract_text_by_selectors(card, self.selectors['product_price'])
                    product_data['price'] = price or "Цена не указана"

                    rating = self.extract_text_by_selectors(card, self.selectors['product_rating'])
                    product_data['rating'] = rating

                    img_element = None
                    for selector in self.selectors['product_image']:
                        try:
                            img_element = card.find_element(By.CSS_SELECTOR, selector)
                            break
                        except NoSuchElementException:
                            continue
                    
                    if img_element:
                        img_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
                        if img_url:
                            safe_name = re.sub(r'[^\w\s-]', '', product_data['name'][:30])
                            safe_name = re.sub(r'[-\s]+', '_', safe_name)
                            safe_name_md5 = hashlib.md5(safe_name.encode('utf-8')).hexdigest()
                            img_filename = f"{safe_name_md5}_{product_id}_{i+1}.jpg"

                            img_path = self.download_image(img_url, img_filename)
                            product_data['image_url'] = img_url
                            product_data['image_path'] = img_path
                        else:
                            product_data['image_url'] = None
                            product_data['image_path'] = None
                    else:
                        product_data['image_url'] = None
                        product_data['image_path'] = None
                    
                    products.append(product_data)
                    print(f"Processed product #{i+1}: {product_data['name']}")
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Fail in product #{i+1}: {e}")
                    continue
            
            print(f"Total proccessed on page: {len(products)}")
            return products
            
        except Exception as e:
            print(f"parse_products fail: {e}")
            return products
    
    def parse_multiple_pages(self, max_pages=5):
        print("Start parse_multiple_pages")
        all_products = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                print(f"\nProccessing page #{current_page}")

                page_products = self.parse_products()

                for product in page_products:
                    product['page_number'] = current_page
                
                all_products.extend(page_products)
                
                print(f"Page #{current_page}: {len(page_products)} products proccessed")

                if current_page < max_pages:
                    self.go_to_next_page()
                    current_page += 1
                    time.sleep(3)
                else:
                    break
                    
            except Exception as e:
                print(f"parse_multiple_pages fail on page #{current_page}: {e}")
                break
        
        return all_products
    
    def save_data(self, products, query):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query)
        safe_query = re.sub(r'[-\s]+', '_', safe_query)

        csv_filename = f"data/wb_{safe_query}_{timestamp}.csv"
        with open(csv_filename, 'a', encoding='utf-8') as f:
            f.write("id,name,price,image_url,image_path,rating,page\n")
            for product in products:
                name = str(product.get("name", "")).replace('"', '""')
                price = str(product.get("price", "")).replace('"', '""')
                rating = str(product.get("rating", "")).replace('"', '""')
                page_num = str(product.get("page_number", "1"))
                
                f.write(f'"{product.get("id", "")}","{name}","{price}","{product.get("image_url", "")}","{product.get("image_path", "")}","{rating}","{page_num}"\n')
        print(f"Saved to csv: {csv_filename}")

    
    def close(self):
        if self.driver:
            self.driver.quit()
    
    def parse_with_pages(self, query, max_pages):

        print("Start parse_with_pages")
        
        try:
            self.setup_driver()
            self.search_products(query)
            products = self.parse_multiple_pages(max_pages)
            self.save_data(products, query)
            return products
            
        except Exception as e:
            print(f"parse_with_pages failed: {e}")
            return []
        
        finally:
            self.close()



def main():

    SEARCH_QUERY = "iphone"
    MAX_PAGES = 1

    parser = WildberriesParserV2()

    parser.parse_with_pages(
        query=SEARCH_QUERY,
        max_pages=MAX_PAGES
    )


if __name__ == "__main__":
    main()