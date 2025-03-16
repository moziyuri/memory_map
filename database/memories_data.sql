-- Import vzpomínek do databáze
INSERT INTO memories (text, location, coordinates, source, keywords, date) VALUES
-- Sudety a poválečné vysídlení
('Pamatuji si den, kdy jsme museli opustit náš dům v Jablonci. Bylo mi tehdy 12 let. Otec nás večer probudil a měli jsme jen dvě hodiny na sbalení. Mohli jsme si vzít jen to, co uneseme v rukou. Většina našeho majetku tam zůstala. Přestěhovali nás do sběrného tábora v Liberci a později do Německa.',
'Jablonec nad Nisou', 
ST_SetSRID(ST_MakePoint(15.171, 50.724), 4326),
'Rozhovor s pamětníkem Hans Müller (*1934), rok události: 1946',
ARRAY['vysídlení', 'Sudety', 'Němci', 'Jablonec', 'odsun'],
'1946'),

('Když jsme se do Karlových Varů nastěhovali v létě 1946, město bylo jako vylidněné. Naše rodina dostala byt po německé rodině Schneiderových. V bytě zůstal nábytek, oblečení, dokonce i fotografie. Bylo mi to tehdy líto, ale rodiče říkali, že ti lidé se dopustili hrozných věcí za války.',
'Karlovy Vary',
ST_SetSRID(ST_MakePoint(12.880, 50.231), 4326),
'Paměť národa - Marie Horáková (*1939), rok události: 1946',
ARRAY['dosídlení', 'Sudety', 'Karlovy Vary', 'konfiskace', 'osídlování'],
'1946'),

('Narodil jsem se v Chebu v roce 1932. Můj otec byl sudetský Němec, matka Češka. Po válce jsme jako jedni z mála Němců dostali povolení zůstat. Ale byla to těžká doba. Ve škole mi říkali "Němčour", nemohl jsem si najít kamarády. Táta pracoval v dolech, byla to jediná práce, kterou mohl jako Němec dostat.',
'Cheb',
ST_SetSRID(ST_MakePoint(12.374, 50.080), 4326),
'Rozhovor s pamětníkem Josef Winkler (*1932), rok události: 1946',
ARRAY['Sudety', 'Cheb', 'smíšená rodina', 'diskriminace', 'poválečná doba'],
'1946'),

-- Protektorát a druhá světová válka
('Nejhorší bylo, když gestapo zatklo mého bratra. Bylo mi 10 let. Přišli v noci, probudili nás a prohledali celý dům. Bratra odvedli a už jsme ho nikdy neviděli. Až po válce jsme se dozvěděli, že zemřel v koncentračním táboře Flossenbürg. Bylo mu jen 22 let a byl v odboji.',
'Praha',
ST_SetSRID(ST_MakePoint(14.423, 50.088), 4326),
'Rozhovor s pamětníkem Helena Dvořáková (*1933), rok události: 1943',
ARRAY['Protektorát', 'gestapo', 'odboj', 'koncentrační tábor', 'Praha'],
'1943'),

-- Sametová revoluce 1989
('17. listopadu 1989 jsem byl na Národní třídě. Šel jsem v průvodu studentů, když nás najednou obklíčily jednotky pohotovostního pluku. Nebylo kam utéct. Začali nás mlátit obušky, i když jsme byli zcela nenásilní. Viděl jsem, jak zbili jednoho kluka tak, že zůstal ležet na zemi. Měl jsem štěstí, že jsem se dostal do podloubí a pak bočním východem pryč.',
'Praha - Národní třída',
ST_SetSRID(ST_MakePoint(14.418, 50.081), 4326),
'Paměť národa - Martin Šimek (*1968), rok události: 1989',
ARRAY['17. listopad', 'Národní třída', 'sametová revoluce', 'demonstrace', 'násilí'],
'1989'),

-- Povodně 1997 a 2002
('Když v roce 1997 přišla velká voda, měla jsem pocit, že se svět zbláznil. Z okna našeho domu v Troubkách jsem viděla, jak se voda valí ulicí. Soused křičel, abychom utekli. Manžel nechtěl opustit dům, ale nakonec jsme museli. Vzali jsme jen doklady a psa. Když jsme se za tři dny vrátili, z našeho domu zbyla jen hromada sutin.',
'Troubky',
ST_SetSRID(ST_MakePoint(17.347, 49.431), 4326),
'Rozhovor s pamětníkem Marie Horáková (*1955), rok události: 1997',
ARRAY['povodně 1997', 'Troubky', 'přírodní katastrofa', 'záplavy', 'ztráta domova'],
'1997'),

('Povodně v roce 2002 nás zasáhly nečekaně. V Českých Budějovicích to nejdřív vypadalo, že voda nepřekročí protipovodňové zábrany. Ale pak se během několika hodin všechno změnilo. Záchranáři nás evakuovali na člunu. Tehdy jsem pochopil, jak je člověk bezmocný proti přírodě.',
'České Budějovice',
ST_SetSRID(ST_MakePoint(14.475, 48.975), 4326),
'Paměť národa - Jan Mašek (*1960), rok události: 2002',
ARRAY['povodně 2002', 'České Budějovice', 'přírodní katastrofa', 'evakuace', 'solidarita'],
'2002'),

-- Důlní neštěstí
('Můj otec byl horníkem na Dole Dukla. V roce 1961 tam byl při tom velkém výbuchu. Přežil jen díky tomu, že pracoval v jiné části dolu. Vybavuji si, jak jsme čekali před dolem, jestli vyjde ven. Když jsme ho uviděli, maminka omdlela štěstím. Jeho nejlepší kamarád Karel ale zahynul.',
'Havířov',
ST_SetSRID(ST_MakePoint(18.432, 49.789), 4326),
'Rodinná historie - Pavel Sikora (*1953), rok události: 1961',
ARRAY['důlní neštěstí', 'Důl Dukla', 'Havířov', 'hornictví', 'výbuch'],
'1961'),

-- Kolektivizace
('Když přišla kolektivizace, děda odmítl vstoupit do JZD. Byl sedlák celý život a říkal, že to raději všechno nechá ležet ladem. Pak přišli esenbáci a odvedli ho. Dostal dva roky za sabotáž. Vrátil se jako zlomený člověk. Náš statek mezitím zabavili a pole přidali k družstvu.',
'Prachatice',
ST_SetSRID(ST_MakePoint(13.881, 49.260), 4326),
'Rozhovor s pamětníkem Josef Kadlec (*1943), rok události: 1953',
ARRAY['kolektivizace', 'JZD', 'Šumava', 'perzekuce zemědělců', 'komunismus'],
'1953'),

-- Industrializace
('Ostrava byla v 50. letech úplně jiné město. Všude se stavělo, všude byl prach a hluk. Přijížděli sem lidé z celé republiky pracovat v hutích a dolech. Byl tu život, ale vzduch byl k nedýchání. Když jsem věšela prádlo, za hodinu bylo černé od sazí.',
'Ostrava',
ST_SetSRID(ST_MakePoint(18.283, 49.830), 4326),
'Rozhovor s pamětníkem Božena Nováková (*1935), rok události: 1955',
ARRAY['industrializace', 'Ostrava', 'hutě', 'znečištění', 'socialistická výstavba'],
'1955'),

-- Restituce
('Když po revoluci přišla možnost restitucí, hned jsme žádali o vrácení našeho statku a pozemků. Děda se toho už nedožil, ale chtěli jsme, aby se spravedlnosti stalo zadost. Jenže to vůbec nebylo jednoduché. Původní budovy byly přestavěné, pole zanedbané. Trvalo 8 let soudů, než jsme dostali aspoň část majetku zpět.',
'Humpolec',
ST_SetSRID(ST_MakePoint(14.722, 49.667), 4326),
'Rozhovor s pamětníkem František Veselý (*1950), rok události: 1992',
ARRAY['restituce', 'komunismus', 'majetek', 'spravedlnost', 'soudy'],
'1992'),

('Rodiče dostali v restituci zpět obchod v Praze, který jim komunisté sebrali. Ale byl ve strašném stavu. Museli jsme si vzít obrovskou půjčku, abychom ho opravili. Nakonec jsme ho stejně museli prodat, protože přišly supermarkety a malé obchody krachovaly.',
'Praha - Žižkov',
ST_SetSRID(ST_MakePoint(14.425, 50.100), 4326),
'Paměť národa - Jana Krejčová (*1955), rok události: 1994',
ARRAY['restituce', 'Praha', 'obchod', 'transformace', 'privatizace'],
'1994'),

-- Vzpomínky na 60. léta
('V šedesátých letech to bylo krásné období. Byl jsem mladý, hrál jsem v rockové kapele, nosil dlouhé vlasy. Rodiče byli zděšení, ale nám to bylo jedno. Poslouchali jsme západní hudbu, Beatles, Rolling Stones. Chodili jsme do Music F Clubu na Smíchově. Pak přišli Rusové a všechno skončilo.',
'Praha - Smíchov',
ST_SetSRID(ST_MakePoint(14.405, 50.076), 4326),
'Rozhovor s pamětníkem Milan Dvořák (*1947), rok události: 1965',
ARRAY['60. léta', 'Praha', 'bigbít', 'Pražské jaro', 'normalizace'],
'1965'),

('V roce 1965 jsem jela poprvé do Jugoslávie. To bylo něco! Moře, slunce, svoboda. Setkali jsme se tam s Němci ze západu. Povídali jsme si s nimi a bylo to jako z jiného světa. Měli džíny, poslouchali muziku, o které jsme jen slyšeli. Když jsem se vrátila domů, všechno mi připadalo šedivé a smutné.',
'Brno',
ST_SetSRID(ST_MakePoint(16.608, 49.195), 4326),
'Paměť národa - Eva Malá (*1945), rok události: 1965',
ARRAY['60. léta', 'cestování', 'Jugoslávie', 'svoboda', 'železná opona'],
'1965'),

-- Zkušenosti pamětníků z disentu
('Psali jsme samizdat na psacím stroji přes kopíráky. Většinou v noci, kdy děti spaly. Dělali jsme maximálně deset kopií najednou, víc nešlo. Pak jsme to distribuovali mezi známé. Každý, kdo dostal jednu kopii, ji musel dát přečíst dalším lidem. Byl to velký risk. Můj muž byl kvůli tomu ve vězení, ale my jsme pokračovali.',
'Praha - Vinohrady',
ST_SetSRID(ST_MakePoint(14.421, 50.088), 4326),
'Rozhovor s pamětníkem Alena Hromádková (*1948), rok události: 1978',
ARRAY['disent', 'samizdat', 'Praha', 'normalizace', 'perzekuce'],
'1978'),

('Nejvíc mě bolelo, když musela dcera kvůli mně odejít ze školy. Jen proto, že jsem podepsal Chartu 77. Ředitel si ji zavolal a řekl jí, že s takovým otcem nemůže studovat vysokou školu. Bylo jí 19 a chtěla být lékařkou. Musela jít pracovat do továrny.',
'Brno',
ST_SetSRID(ST_MakePoint(16.608, 49.195), 4326),
'Rozhovor s pamětníkem Pavel Kohout (*1935), rok události: 1977',
ARRAY['Charta 77', 'disent', 'Brno', 'perzekuce', 'normalizace'],
'1977'),

-- Komunistický režim
('Po únoru 1948 zavřeli náš rodinný obchod. Děda ho vedl 30 let a pak přišli a řekli, že je konec soukromého podnikání. Zboží zkonfiskovali, prostory dostal národní podnik. Děda se z toho psychicky zhroutil a za rok zemřel. Říkal, že mu vzali smysl života.',
'České Budějovice',
ST_SetSRID(ST_MakePoint(14.475, 48.975), 4326),
'Rozhovor s pamětníkem Jaroslav Beneš (*1942), rok události: 1948',
ARRAY['únor 1948', 'znárodnění', 'komunismus', 'České Budějovice', 'soukromý podnikatel'],
'1948'),

('Byla jsem 9 let v Jáchymově jako politický vězeň. Pracovala jsem v uranových dolech. Bylo nás tam hodně žen, většinou politických vězeňkyň. Podmínky byly strašné, radioaktivní prach všude, nedostatek jídla, násilí od dozorců. Mnoho žen tam zemřelo.',
'Jáchymov',
ST_SetSRID(ST_MakePoint(12.914, 50.358), 4326),
'Paměť národa - Anna Procházková (*1925), rok události: 1952',
ARRAY['Jáchymov', 'politický vězeň', 'uranové doly', 'komunismus', 'perzekuce'],
'1952'),

('Když jsem při prověrkách v roce 1970 odmítl odsoudit "kontrarevoluce", vyhodili mě z práce. Byl jsem vystudovaný inženýr, ale směl jsem pracovat jen jako topič. Každý den jsem viděl z kotelny své bývalé kolegy v kancelářích. Bylo to ponižující, ale já jsem věděl, že jsem udělal správnou věc.',
'Hradec Králové',
ST_SetSRID(ST_MakePoint(15.832, 50.207), 4326),
'Paměť národa - Josef Kučera (*1940), rok události: 1970',
ARRAY['prověrky', 'normalizace', 'Hradec Králové', 'perzekuce', 'topič'],
'1970'); 