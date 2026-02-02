import requests
from bs4 import BeautifulSoup
import json
import time
import re

# URL base
BASE_URL = "https://dblegends.net"
CHARACTERS_URL = f"{BASE_URL}/characters"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException as e:
        print(f"Erro ao aceder a {url}: {e}")
        return None

def scrape_character_details(char_url, basic_info):
    soup = get_soup(char_url)
    if not soup:
        return basic_info

    details = basic_info.copy()
    
    # --- 1. Extrair Stats ---
    stats = {}
    all_ps = soup.find_all("p", class_="mx-3 my-0")
    for p in all_ps:
        text = p.get_text(strip=True)
        if ":" in text:
            key, value = text.split(":", 1)
            stats[key.strip()] = value.strip()
    details['stats'] = stats

    # --- 2. Extrair Habilidades (CORRIGIDO) ---
    
    def extract_ability_section(header_text):
        abilities = []
        
        # ALTERAÇÃO AQUI: 
        # Usamos 'rf"^\s*{header_text}"' para garantir que o texto COMEÇA com a palavra.
        # \s* permite espaços em branco antes da palavra (comum em HTML).
        # Isto impede que "Z Ability" encontre "Limited Z Ability".
        pattern = re.compile(rf"^\s*{header_text}", re.IGNORECASE)
        
        header = soup.find("div", class_="ability-name", string=pattern)
        
        if header:
            # Tenta encontrar o container principal
            container = header.find_parent("div").find_parent("div")
            
            # Procura por tab-content (estrutura com abas I, II, III, IV)
            tab_content = container.find_next("div", class_="tab-content")
            if tab_content:
                panes = tab_content.find_all("div", class_="tab-pane")
                for pane in panes:
                    level = pane.get("aria-labelledby", "").replace("-tab", "")
                    desc = pane.get_text(" ", strip=True)
                    abilities.append({"level_id": level, "description": desc})
            else:
                # Se não houver abas, é texto direto (ex: Main Ability)
                next_div = header.find_parent("div").find_next_sibling("div")
                if next_div:
                    abilities.append(next_div.get_text(" ", strip=True))
        return abilities

    # Agora a busca por "Z Ability" vai ignorar "Limited Z Ability" porque não começa por "Z"
    details['z_abilities'] = extract_ability_section("Z Ability")
    
    # Adicionei isto caso queiras os dados da Limited Z Ability separadamente
    details['limited_z_ability'] = extract_ability_section("Limited Z Ability")
    
    details['main_ability'] = extract_ability_section("Main Ability")
    details['unique_abilities'] = extract_ability_section("Unique Ability")
    details['ultra_ability'] = extract_ability_section("Ultra Ability")
    
    if details.get('zenkai_id') and details.get('zenkai_id') != "-1":
        details['zenkai_abilities'] = extract_ability_section("Zenkai Ability")

    # --- 3. Extrair Arts ---
    arts = []
    art_headers = soup.find_all("div", class_="ability-name", string=re.compile("Arts Card"))
    for art_h in art_headers:
        parent = art_h.find_parent("div")
        content_div = parent.find_next_sibling("div")
        if content_div:
            art_name = art_h.get_text(strip=True)
            art_desc = content_div.get_text(" ", strip=True)
            arts.append({"type": art_name, "effect": art_desc})
    details['arts'] = arts

    # --- 4. Tags Visuais ---
    visual_tags = []
    trait_links = soup.find_all("a", class_="trait-thumb")
    for link in trait_links:
        tag_name = link.find("div", class_="name")
        if tag_name:
            visual_tags.append(tag_name.get_text(strip=True))
    details['visual_tags'] = visual_tags

    return details

def main():
    print(f"A iniciar scraping de: {CHARACTERS_URL}")
    soup = get_soup(CHARACTERS_URL)
    
    if not soup:
        print("Falha ao carregar a página principal.")
        return

    character_links = soup.find_all("a", class_="chara-list")
    all_characters = []
    total_chars = len(character_links)
    
    print(f"Encontrados {total_chars} personagens. A começar extração detalhada...")

    for index, link in enumerate(character_links):
        # --- Extração da Imagem ---
        img_tag = link.find("img")
        image_url = ""
        if img_tag and img_tag.get("src"):
            raw_src = img_tag.get("src")
            if not raw_src.startswith("http"):
                image_url = f"{BASE_URL}/{raw_src.lstrip('/')}"
            else:
                image_url = raw_src
        
        char_id_db = link.get('href').split('/')[-1]
        
        basic_data = {
            "internal_id": char_id_db,
            "name": link.get('data-charaname'),
            "form": link.get('data-charaformname'),
            "element": link.get('data-element'),
            "rarity": link.get('data-rarity'),
            "zenkai_id": link.get('data-zenkai'),
            "is_lf": link.get('data-lf') == "1",
            "tags_ids": link.get('data-tags').split() if link.get('data-tags') else [],
            "url": f"{BASE_URL}{link.get('href')}",
            "image": image_url
        }

        # REMOVE O COMENTÁRIO ABAIXO PARA SACAR TODOS (está limitado a 10 para teste)
        # if index >= 10: break 
        
        print(f"[{index+1}/{total_chars}] A extrair: {basic_data['name']} ({basic_data['rarity']})")
        
        full_data = scrape_character_details(basic_data['url'], basic_data)
        all_characters.append(full_data)
        
        time.sleep(0.5)

    with open("dbl_characters_full.json", "w", encoding="utf-8") as f:
        json.dump(all_characters, f, ensure_ascii=False, indent=4)

    print("Concluído! Dados guardados em 'dbl_characters_full.json'")

if __name__ == "__main__":
    main()
