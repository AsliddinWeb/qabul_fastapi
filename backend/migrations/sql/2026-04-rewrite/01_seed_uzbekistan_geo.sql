-- 02: Seed O'zbekiston geography (14 regions, ~200 districts).
-- Source: old/qabul-sayt-main/apps/regions/management/commands/populate_regions.py
BEGIN;

-- Country
INSERT INTO countries (name)
VALUES ('O''zbekiston')
ON CONFLICT (name) DO NOTHING;

-- Helper: write into a temp table, then loop. Use simple INSERT...SELECT pattern.

-- Regions
WITH uz AS (SELECT id FROM countries WHERE name = 'O''zbekiston')
INSERT INTO regions (name, country_id)
SELECT r.name, uz.id
FROM uz, (VALUES
    ('Toshkent shahri'),
    ('Toshkent viloyati'),
    ('Andijon'),
    ('Namangan'),
    ('Farg''ona'),
    ('Samarqand'),
    ('Buxoro'),
    ('Qashqadaryo'),
    ('Surxondaryo'),
    ('Jizzax'),
    ('Sirdaryo'),
    ('Navoiy'),
    ('Xorazm'),
    ('Qoraqalpog''iston Respublikasi')
) AS r(name)
ON CONFLICT (name, country_id) DO NOTHING;

-- Districts
INSERT INTO districts (name, region_id)
SELECT d.name, r.id
FROM regions r,
LATERAL (VALUES
    -- Toshkent shahri
    ('Toshkent shahri', 'Bektemir'),
    ('Toshkent shahri', 'Chilonzor'),
    ('Toshkent shahri', 'Hamza (Yashnobod)'),
    ('Toshkent shahri', 'Mirobod'),
    ('Toshkent shahri', 'Mirzo Ulug''bek'),
    ('Toshkent shahri', 'Olmazor'),
    ('Toshkent shahri', 'Sergeli'),
    ('Toshkent shahri', 'Shayxontohur'),
    ('Toshkent shahri', 'Uchtepa'),
    ('Toshkent shahri', 'Yakkasaroy'),
    ('Toshkent shahri', 'Yunusobod'),
    -- Toshkent viloyati
    ('Toshkent viloyati', 'Angren'),
    ('Toshkent viloyati', 'Bekobod'),
    ('Toshkent viloyati', 'Bo''ka'),
    ('Toshkent viloyati', 'Bo''stonliq'),
    ('Toshkent viloyati', 'Chinoz'),
    ('Toshkent viloyati', 'Ohangaron'),
    ('Toshkent viloyati', 'Oqqo''rg''on'),
    ('Toshkent viloyati', 'Parkent'),
    ('Toshkent viloyati', 'Piskent'),
    ('Toshkent viloyati', 'Quyi Chirchiq'),
    ('Toshkent viloyati', 'Toshkent tumani'),
    ('Toshkent viloyati', 'Yangiyo''l'),
    ('Toshkent viloyati', 'Yuqori Chirchiq'),
    ('Toshkent viloyati', 'Zangiota'),
    -- Andijon
    ('Andijon', 'Andijon shahri'),
    ('Andijon', 'Andijon tumani'),
    ('Andijon', 'Asaka'),
    ('Andijon', 'Baliqchi'),
    ('Andijon', 'Bo''z'),
    ('Andijon', 'Buloqboshi'),
    ('Andijon', 'Izboskan'),
    ('Andijon', 'Jalaquduq'),
    ('Andijon', 'Qo''rg''ontepa'),
    ('Andijon', 'Marhamat'),
    ('Andijon', 'Oltinko''l'),
    ('Andijon', 'Paxtaobod'),
    ('Andijon', 'Shahrixon'),
    ('Andijon', 'Ulug''nor'),
    ('Andijon', 'Xo''jaobod'),
    -- Namangan
    ('Namangan', 'Namangan shahri'),
    ('Namangan', 'Chortoq'),
    ('Namangan', 'Chust'),
    ('Namangan', 'Kosonsoy'),
    ('Namangan', 'Mingbuloq'),
    ('Namangan', 'Norin'),
    ('Namangan', 'Pop'),
    ('Namangan', 'To''raqo''rg''on'),
    ('Namangan', 'Uchqo''rg''on'),
    ('Namangan', 'Yangiqo''rg''on'),
    -- Farg'ona
    ('Farg''ona', 'Farg''ona shahri'),
    ('Farg''ona', 'Qo''qon'),
    ('Farg''ona', 'Marg''ilon'),
    ('Farg''ona', 'Beshariq'),
    ('Farg''ona', 'Bog''dod'),
    ('Farg''ona', 'Buvayda'),
    ('Farg''ona', 'Dang''ara'),
    ('Farg''ona', 'Furqat'),
    ('Farg''ona', 'Oltiariq'),
    ('Farg''ona', 'Quva'),
    ('Farg''ona', 'Rishton'),
    ('Farg''ona', 'So''x'),
    ('Farg''ona', 'Toshloq'),
    ('Farg''ona', 'Uchko''prik'),
    ('Farg''ona', 'Yozyovon'),
    -- Samarqand
    ('Samarqand', 'Samarqand shahri'),
    ('Samarqand', 'Bulung''ur'),
    ('Samarqand', 'Ishtixon'),
    ('Samarqand', 'Jomboy'),
    ('Samarqand', 'Kattaqo''rg''on'),
    ('Samarqand', 'Kattaqo''rg''on tumani'),
    ('Samarqand', 'Narpay'),
    ('Samarqand', 'Nurobod'),
    ('Samarqand', 'Oqdaryo'),
    ('Samarqand', 'Paxtachi'),
    ('Samarqand', 'Payariq'),
    ('Samarqand', 'Pastdarg''om'),
    ('Samarqand', 'Samarqand tumani'),
    ('Samarqand', 'Tayloq'),
    ('Samarqand', 'Urgut'),
    -- Buxoro
    ('Buxoro', 'Buxoro shahri'),
    ('Buxoro', 'Buxoro tumani'),
    ('Buxoro', 'G''ijduvon'),
    ('Buxoro', 'Jondor'),
    ('Buxoro', 'Kogon'),
    ('Buxoro', 'Kogon tumani'),
    ('Buxoro', 'Olot'),
    ('Buxoro', 'Peshku'),
    ('Buxoro', 'Qorako''l'),
    ('Buxoro', 'Qorovulbozor'),
    ('Buxoro', 'Romitan'),
    ('Buxoro', 'Shofirkon'),
    ('Buxoro', 'Vobkent'),
    -- Qashqadaryo
    ('Qashqadaryo', 'Qarshi shahri'),
    ('Qashqadaryo', 'Qarshi tumani'),
    ('Qashqadaryo', 'Dehqonobod'),
    ('Qashqadaryo', 'G''uzor'),
    ('Qashqadaryo', 'Kasbi'),
    ('Qashqadaryo', 'Kitob'),
    ('Qashqadaryo', 'Koson'),
    ('Qashqadaryo', 'Mirishkor'),
    ('Qashqadaryo', 'Muborak'),
    ('Qashqadaryo', 'Nishon'),
    ('Qashqadaryo', 'Shahrisabz'),
    ('Qashqadaryo', 'Shahrisabz tumani'),
    ('Qashqadaryo', 'Yakkabog'''),
    ('Qashqadaryo', 'Chiroqchi'),
    -- Surxondaryo
    ('Surxondaryo', 'Termiz shahri'),
    ('Surxondaryo', 'Angor'),
    ('Surxondaryo', 'Bandixon'),
    ('Surxondaryo', 'Boysun'),
    ('Surxondaryo', 'Denov'),
    ('Surxondaryo', 'Jarqo''rg''on'),
    ('Surxondaryo', 'Qiziriq'),
    ('Surxondaryo', 'Qumqo''rg''on'),
    ('Surxondaryo', 'Muzrabot'),
    ('Surxondaryo', 'Oltinsoy'),
    ('Surxondaryo', 'Sariosiyo'),
    ('Surxondaryo', 'Sherobod'),
    ('Surxondaryo', 'Sho''rchi'),
    ('Surxondaryo', 'Termiz tumani'),
    -- Jizzax
    ('Jizzax', 'Jizzax shahri'),
    ('Jizzax', 'Arnasoy'),
    ('Jizzax', 'Baxmal'),
    ('Jizzax', 'Dostlik'),
    ('Jizzax', 'Forish'),
    ('Jizzax', 'G''allaorol'),
    ('Jizzax', 'Sharof Rashidov'),
    ('Jizzax', 'Mirzacho''l'),
    ('Jizzax', 'Paxtakor'),
    ('Jizzax', 'Yangiobod'),
    ('Jizzax', 'Zafarobod'),
    ('Jizzax', 'Zarbdor'),
    ('Jizzax', 'Zomin'),
    -- Sirdaryo
    ('Sirdaryo', 'Guliston shahri'),
    ('Sirdaryo', 'Boyovut'),
    ('Sirdaryo', 'Guliston tumani'),
    ('Sirdaryo', 'Mirzaobod'),
    ('Sirdaryo', 'Oqoltin'),
    ('Sirdaryo', 'Sayxunobod'),
    ('Sirdaryo', 'Sardoba'),
    ('Sirdaryo', 'Sirdaryo'),
    ('Sirdaryo', 'Xovos'),
    ('Sirdaryo', 'Shirin'),
    ('Sirdaryo', 'Yangiyer'),
    -- Navoiy
    ('Navoiy', 'Navoiy shahri'),
    ('Navoiy', 'Karmana'),
    ('Navoiy', 'Konimex'),
    ('Navoiy', 'Navbahor'),
    ('Navoiy', 'Nurota'),
    ('Navoiy', 'Xatirchi'),
    ('Navoiy', 'Qiziltepa'),
    ('Navoiy', 'Tomdi'),
    ('Navoiy', 'Uchquduq'),
    ('Navoiy', 'Zarafshon'),
    -- Xorazm
    ('Xorazm', 'Urganch shahri'),
    ('Xorazm', 'Bog''ot'),
    ('Xorazm', 'Gurlan'),
    ('Xorazm', 'Hazorasp'),
    ('Xorazm', 'Xiva'),
    ('Xorazm', 'Xiva tumani'),
    ('Xorazm', 'Qo''shko''pir'),
    ('Xorazm', 'Shovot'),
    ('Xorazm', 'Urganch tumani'),
    ('Xorazm', 'Yangiariq'),
    ('Xorazm', 'Yangibozor'),
    -- Qoraqalpog'iston Respublikasi
    ('Qoraqalpog''iston Respublikasi', 'Nukus shahri'),
    ('Qoraqalpog''iston Respublikasi', 'Amudaryo'),
    ('Qoraqalpog''iston Respublikasi', 'Beruniy'),
    ('Qoraqalpog''iston Respublikasi', 'Chimboy'),
    ('Qoraqalpog''iston Respublikasi', 'Ellikqal''a'),
    ('Qoraqalpog''iston Respublikasi', 'Kegeyli'),
    ('Qoraqalpog''iston Respublikasi', 'Mo''ynoq'),
    ('Qoraqalpog''iston Respublikasi', 'Nukus tumani'),
    ('Qoraqalpog''iston Respublikasi', 'Qo''ng''irot'),
    ('Qoraqalpog''iston Respublikasi', 'Qanliko''l'),
    ('Qoraqalpog''iston Respublikasi', 'Qorao''zak'),
    ('Qoraqalpog''iston Respublikasi', 'Shumanay'),
    ('Qoraqalpog''iston Respublikasi', 'Taxtako''pir'),
    ('Qoraqalpog''iston Respublikasi', 'To''rtko''l'),
    ('Qoraqalpog''iston Respublikasi', 'Xo''jayli')
) AS d(region_name, name)
WHERE r.name = d.region_name
ON CONFLICT (name, region_id) DO NOTHING;

-- Sample additional countries for transfer diploms
INSERT INTO countries (name)
VALUES
    ('Qozog''iston'),
    ('Rossiya'),
    ('Qirg''iziston'),
    ('Tojikiston'),
    ('Turkmaniston')
ON CONFLICT (name) DO NOTHING;

COMMIT;
