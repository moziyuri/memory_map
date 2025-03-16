# Uživatelská příručka MemoryMap

> **Aplikace vytvořená za účelem pohovoru** - Tento projekt demonstruje praktické dovednosti v oblasti full-stack vývoje.

## Úvod

MemoryMap je aplikace pro ukládání vzpomínek spojených s geografickými místy. Umožňuje zaznamenat vzpomínky, připojit je ke konkrétním místům na mapě a později je procházet, vyhledávat a filtrovat.

## Přístup k aplikaci

**URL aplikace**: [https://stanislavhoracekmemorymap.streamlit.app](https://stanislavhoracekmemorymap.streamlit.app)

## Základní funkce

### 1. Prohlížení mapy vzpomínek

Po otevření aplikace se zobrazí interaktivní mapa s barevnými piny reprezentujícími uložené vzpomínky.

- **Přiblížení/oddálení**: použijte kolečko myši nebo tlačítka + a - v pravém horním rohu mapy
- **Posouvání mapy**: klikněte a táhněte myší
- **Zobrazení detailu vzpomínky**: klikněte na pin na mapě - otevře se pop-up okno s obsahem vzpomínky
- **Změna podkladové mapy**: použijte ikonu vrstev v pravém horním rohu mapy

### 2. Přidání nové vzpomínky

Pro přidání nové vzpomínky:

1. Klikněte na tlačítko "Přidat vzpomínku" v bočním panelu
2. Na mapě se aktivuje režim přidávání - klikněte na požadované místo na mapě, kam chcete vzpomínku umístit
3. Vyplňte formulář:
   - **Text vzpomínky**: Popište svou vzpomínku (povinné pole)
   - **Místo**: Zadejte název místa (povinné pole) nebo ponechte automaticky vyplněný název podle kliknutí na mapu
   - **Zdroj**: Volitelně uveďte zdroj vzpomínky (např. "Osobní deník", "Rozhovor s babičkou")
   - **Datum**: Volitelně uveďte datum související se vzpomínkou
4. Klikněte na tlačítko "Uložit vzpomínku"
5. Na mapě se ihned zobrazí nový pin s vaší vzpomínkou

### 3. Pop-up okna s vzpomínkami

Pro zobrazení detailu vzpomínky:

1. Klikněte na libovolný pin na mapě
2. Otevře se pop-up okno obsahující:
   - Text vzpomínky
   - Místo
   - Datum (pokud bylo zadáno)
   - Zdroj (pokud byl zadán)
   - Klíčová slova automaticky extrahovaná z textu
3. Pop-up okno zavřete kliknutím na křížek nebo kliknutím mimo okno

### 4. Vyhledávání vzpomínek

Pro vyhledávání ve vzpomínkách:

1. Zadejte hledaný výraz do pole "Vyhledat vzpomínky"
2. Výsledky se automaticky filtrují podle:
   - Textu vzpomínky
   - Názvu místa
   - Klíčových slov
   - Zdroje

### 5. Filtrování vzpomínek

Vzpomínky lze filtrovat podle různých kritérií:

1. **Podle místa**: Vyberte místo ze seznamu
2. **Podle data**: Použijte posuvník pro výběr časového období
3. **Podle klíčových slov**: Vyberte klíčová slova ze seznamu

## Tipy pro efektivní používání

- **Detailní popis**: Čím detailnější popis vzpomínky, tím lépe bude fungovat automatická extrakce klíčových slov
- **Přesné umístění**: Pro přesné umístění vzpomínky využijte možnost přiblížení mapy před kliknutím na místo
- **Struktura textu**: Pro lepší čitelnost používejte ve vzpomínkách odstavce

## Řešení problémů

### Vzpomínka se nezobrazuje na mapě

- Ujistěte se, že jste po vyplnění formuláře klikli na tlačítko "Uložit vzpomínku"
- Obnovte stránku pomocí tlačítka F5
- Ujistěte se, že máte aktivní internetové připojení

### Nelze přidat vzpomínku na mapu

- Zkontrolujte, zda je aktivován režim přidávání vzpomínky
- Ujistěte se, že jsou vyplněna všechna povinná pole (text a místo)
- Zkontrolujte, zda máte aktivní internetové připojení

### Pop-up okna se nezobrazují

- Zkontrolujte, zda není ve vašem prohlížeči blokováno vyskakovací okna
- Zkuste použít jiný webový prohlížeč

### Pomalé načítání aplikace

- Při velkém množství vzpomínek může být načítání pomalejší
- Zkuste obnovit stránku nebo se vrátit později

## O aplikaci

MemoryMap je ukázková aplikace vytvořená za účelem pohovoru. Demonstruje praktické dovednosti v oblasti:
- Full-stack vývoje webových aplikací
- Práce s interaktivními mapami
- Využití PostgreSQL s PostGIS pro geografická data
- Moderních UI/UX přístupů pro uživatelsky přívětivé aplikace

## Kontakt a podpora

Pokud narazíte na problémy nebo máte návrhy na zlepšení, kontaktujte nás na:

- Email: [stanislav.horacek@email.cz](mailto:stanislav.horacek@email.cz)
- GitHub: [https://github.com/stanislavhoracek/memorymap](https://github.com/stanislavhoracek/memorymap) 