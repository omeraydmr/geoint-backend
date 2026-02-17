#!/usr/bin/env python3
"""
Seed Turkish Provinces and Districts

Uses hardcoded data for Turkey's 81 provinces
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.geo import Province, District
import logging
import uuid
from datetime import datetime
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon, MultiPolygon
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Turkey's 81 provinces with approximate coordinates and population
TURKEY_PROVINCES = [
    ("01", "Adana", "Akdeniz", 36.99, 37.00, 2258718),
    ("02", "Adıyaman", "Güneydoğu Anadolu", 38.28, 37.76, 632459),
    ("03", "Afyonkarahisar", "Ege", 30.54, 38.76, 747555),
    ("04", "Ağrı", "Doğu Anadolu", 43.05, 39.72, 535435),
    ("05", "Amasya", "Karadeniz", 35.83, 40.65, 337508),
    ("06", "Ankara", "İç Anadolu", 32.85, 39.93, 5663322),
    ("07", "Antalya", "Akdeniz", 30.71, 36.88, 2619832),
    ("08", "Artvin", "Karadeniz", 41.82, 41.18, 169543),
    ("09", "Aydın", "Ege", 27.85, 37.85, 1148241),
    ("10", "Balıkesir", "Marmara", 27.89, 39.65, 1257590),
    ("11", "Bilecik", "Marmara", 29.98, 40.15, 228673),
    ("12", "Bingöl", "Doğu Anadolu", 40.50, 38.88, 281768),
    ("13", "Bitlis", "Doğu Anadolu", 42.11, 38.40, 353988),
    ("14", "Bolu", "Karadeniz", 31.61, 40.74, 320014),
    ("15", "Burdur", "Akdeniz", 30.29, 37.72, 273799),
    ("16", "Bursa", "Marmara", 29.07, 40.18, 3194720),
    ("17", "Çanakkale", "Marmara", 26.41, 40.15, 557117),
    ("18", "Çankırı", "İç Anadolu", 33.61, 40.60, 195789),
    ("19", "Çorum", "Karadeniz", 34.95, 40.55, 536483),
    ("20", "Denizli", "Ege", 29.09, 37.77, 1040915),
    ("21", "Diyarbakır", "Güneydoğu Anadolu", 40.22, 37.91, 1783431),
    ("22", "Edirne", "Marmara", 26.56, 41.68, 413903),
    ("23", "Elazığ", "Doğu Anadolu", 39.22, 38.68, 591098),
    ("24", "Erzincan", "Doğu Anadolu", 39.49, 39.75, 234747),
    ("25", "Erzurum", "Doğu Anadolu", 41.28, 39.90, 762321),
    ("26", "Eskişehir", "İç Anadolu", 30.52, 39.78, 906093),
    ("27", "Gaziantep", "Güneydoğu Anadolu", 37.38, 37.06, 2154051),
    ("28", "Giresun", "Karadeniz", 38.39, 40.91, 448721),
    ("29", "Gümüşhane", "Karadeniz", 39.48, 40.46, 164521),
    ("30", "Hakkari", "Doğu Anadolu", 43.74, 37.57, 287625),
    ("31", "Hatay", "Akdeniz", 36.20, 36.50, 1686043),
    ("32", "Isparta", "Akdeniz", 30.55, 37.76, 441412),
    ("33", "Mersin", "Akdeniz", 34.64, 36.80, 1916432),
    ("34", "İstanbul", "Marmara", 28.98, 41.01, 15840900),
    ("35", "İzmir", "Ege", 27.14, 38.42, 4462056),
    ("36", "Kars", "Doğu Anadolu", 43.09, 40.61, 285410),
    ("37", "Kastamonu", "Karadeniz", 33.78, 41.39, 383373),
    ("38", "Kayseri", "İç Anadolu", 35.49, 38.72, 1441523),
    ("39", "Kırklareli", "Marmara", 27.23, 41.74, 361836),
    ("40", "Kırşehir", "İç Anadolu", 34.17, 39.14, 242938),
    ("41", "Kocaeli", "Marmara", 29.94, 40.85, 2033441),
    ("42", "Konya", "İç Anadolu", 32.48, 37.87, 2277017),
    ("43", "Kütahya", "Ege", 29.98, 39.42, 580701),
    ("44", "Malatya", "Doğu Anadolu", 38.35, 38.36, 806012),
    ("45", "Manisa", "Ege", 27.43, 38.61, 1468279),
    ("46", "Kahramanmaraş", "Akdeniz", 36.93, 37.58, 1168163),
    ("47", "Mardin", "Güneydoğu Anadolu", 40.74, 37.31, 870374),
    ("48", "Muğla", "Ege", 28.36, 37.22, 1024735),
    ("49", "Muş", "Doğu Anadolu", 41.75, 38.74, 408728),
    ("50", "Nevşehir", "İç Anadolu", 34.71, 38.63, 309914),
    ("51", "Niğde", "İç Anadolu", 34.68, 37.97, 362071),
    ("52", "Ordu", "Karadeniz", 37.88, 40.98, 771932),
    ("53", "Rize", "Karadeniz", 40.52, 41.02, 348608),
    ("54", "Sakarya", "Marmara", 30.40, 40.76, 1042649),
    ("55", "Samsun", "Karadeniz", 36.33, 41.29, 1371076),
    ("56", "Siirt", "Güneydoğu Anadolu", 41.94, 37.93, 331980),
    ("57", "Sinop", "Karadeniz", 35.15, 42.03, 219733),
    ("58", "Sivas", "İç Anadolu", 37.02, 39.75, 646608),
    ("59", "Tekirdağ", "Marmara", 27.51, 40.98, 1096735),
    ("60", "Tokat", "Karadeniz", 36.55, 40.32, 612646),
    ("61", "Trabzon", "Karadeniz", 39.73, 41.00, 818023),
    ("62", "Tunceli", "Doğu Anadolu", 39.55, 39.11, 89396),
    ("63", "Şanlıurfa", "Güneydoğu Anadolu", 38.79, 37.17, 2155285),
    ("64", "Uşak", "Ege", 29.41, 38.68, 373941),
    ("65", "Van", "Doğu Anadolu", 43.38, 38.50, 1196279),
    ("66", "Yozgat", "İç Anadolu", 34.81, 39.82, 421200),
    ("67", "Zonguldak", "Karadeniz", 31.79, 41.46, 588510),
    ("68", "Aksaray", "İç Anadolu", 34.03, 38.37, 429069),
    ("69", "Bayburt", "Karadeniz", 40.26, 40.26, 84843),
    ("70", "Karaman", "İç Anadolu", 33.22, 37.18, 257879),
    ("71", "Kırıkkale", "İç Anadolu", 33.52, 39.85, 290326),
    ("72", "Batman", "Güneydoğu Anadolu", 41.13, 37.89, 634491),
    ("73", "Şırnak", "Güneydoğu Anadolu", 42.46, 37.52, 529615),
    ("74", "Bartın", "Karadeniz", 32.46, 41.58, 198999),
    ("75", "Ardahan", "Doğu Anadolu", 42.70, 41.11, 96161),
    ("76", "Iğdır", "Doğu Anadolu", 44.04, 39.92, 201314),
    ("77", "Yalova", "Marmara", 29.28, 40.66, 291001),
    ("78", "Karabük", "Karadeniz", 32.62, 41.20, 248014),
    ("79", "Kilis", "Güneydoğu Anadolu", 37.12, 36.72, 147919),
    ("80", "Osmaniye", "Akdeniz", 36.25, 37.07, 559405),
    ("81", "Düzce", "Karadeniz", 31.16, 40.84, 397879),
]


async def create_mock_polygon(lon: float, lat: float, size: float = 0.5) -> MultiPolygon:
    """Create a simple square polygon around a center point"""
    poly = Polygon([
        (lon - size, lat - size),
        (lon + size, lat - size),
        (lon + size, lat + size),
        (lon - size, lat + size),
        (lon - size, lat - size),
    ])
    return from_shape(MultiPolygon([poly]), srid=4326)


async def seed_provinces(db):
    """Seed all 81 Turkish provinces"""
    logger.info("🌍 Seeding 81 Turkish provinces...")

    created = 0
    updated = 0

    for code, name, region, lon, lat, population in TURKEY_PROVINCES:
        # Check if exists
        result = await db.execute(select(Province).where(Province.code == code))
        existing = result.scalar_one_or_none()

        # Create geometries
        centroid_geom = from_shape(Point(lon, lat), srid=4326)
        province_geom = await create_mock_polygon(lon, lat, 0.5)

        if existing:
            existing.name = name
            existing.region = region
            existing.population = population
            existing.geom = province_geom
            existing.centroid = centroid_geom
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            province = Province(
                id=uuid.uuid4(),
                code=code,
                name=name,
                region=region,
                population=population,
                area_km2=10000.0,  # Placeholder
                geom=province_geom,
                centroid=centroid_geom,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(province)
            created += 1

        if (created + updated) % 10 == 0:
            await db.commit()
            logger.info(f"   Progress: {created + updated}/81 provinces...")

    await db.commit()
    logger.info(f"✅ Provinces: {created} created, {updated} updated")
    return created, updated


TURKEY_DISTRICTS: dict[str, list[str]] = {
    "01": ["Aladağ", "Ceyhan", "Çukurova", "Feke", "İmamoğlu", "Karaisalı", "Karataş", "Kozan", "Pozantı", "Saimbeyli", "Sarıçam", "Seyhan", "Tufanbeyli", "Yumurtalık", "Yüreğir"],
    "02": ["Besni", "Çelikhan", "Gerger", "Gölbaşı", "Kahta", "Merkez", "Samsat", "Sincik", "Tut"],
    "03": ["Başmakçı", "Bayat", "Bolvadin", "Çay", "Çobanlar", "Dazkırı", "Dinar", "Emirdağ", "Evciler", "Hocalar", "İhsaniye", "İscehisar", "Kızılören", "Merkez", "Sandıklı", "Sinanpaşa", "Sultandağı", "Şuhut"],
    "04": ["Diyadin", "Doğubayazıt", "Eleşkirt", "Hamur", "Merkez", "Patnos", "Taşlıçay", "Tutak"],
    "05": ["Göynücek", "Gümüşhacıköy", "Hamamözü", "Merkez", "Merzifon", "Suluova", "Taşova"],
    "06": ["Akyurt", "Altındağ", "Ayaş", "Balâ", "Beypazarı", "Çamlıdere", "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana", "Kahramankazan", "Kalecik", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"],
    "07": ["Akseki", "Aksu", "Alanya", "Demre", "Döşemealtı", "Elmalı", "Finike", "Gazipaşa", "Gündoğmuş", "İbradı", "Kaş", "Kemer", "Kepez", "Konyaaltı", "Korkuteli", "Kumluca", "Manavgat", "Muratpaşa", "Serik"],
    "08": ["Ardanuç", "Arhavi", "Borçka", "Hopa", "Kemalpaşa", "Merkez", "Murgul", "Şavşat", "Yusufeli"],
    "09": ["Bozdoğan", "Buharkent", "Çine", "Didim", "Efeler", "Germencik", "İncirliova", "Karacasu", "Karpuzlu", "Koçarlı", "Köşk", "Kuşadası", "Kuyucak", "Nazilli", "Söke", "Sultanhisar", "Yenipazar"],
    "10": ["Altıeylül", "Ayvalık", "Balya", "Bandırma", "Bigadiç", "Burhaniye", "Dursunbey", "Edremit", "Erdek", "Gömeç", "Gönen", "Havran", "İvrindi", "Karesi", "Kepsut", "Manyas", "Marmara", "Savaştepe", "Sındırgı", "Susurluk"],
    "11": ["Bozüyük", "Gölpazarı", "İnhisar", "Merkez", "Osmaneli", "Pazaryeri", "Söğüt", "Yenipazar"],
    "12": ["Adaklı", "Genç", "Karlıova", "Kiğı", "Merkez", "Solhan", "Yayladere", "Yedisu"],
    "13": ["Adilcevaz", "Ahlat", "Güroymak", "Hizan", "Merkez", "Mutki", "Tatvan"],
    "14": ["Dörtdivan", "Gerede", "Göynük", "Kıbrıscık", "Mengen", "Merkez", "Mudurnu", "Seben", "Yeniçağa"],
    "15": ["Ağlasun", "Altınyayla", "Bucak", "Çavdır", "Çeltikçi", "Gölhisar", "Karamanlı", "Kemer", "Merkez", "Tefenni", "Yeşilova"],
    "16": ["Büyükorhan", "Gemlik", "Gürsu", "Harmancık", "İnegöl", "İznik", "Karacabey", "Keles", "Kestel", "Mudanya", "Mustafakemalpaşa", "Nilüfer", "Orhaneli", "Orhangazi", "Osmangazi", "Yenişehir", "Yıldırım"],
    "17": ["Ayvacık", "Bayramiç", "Biga", "Bozcaada", "Çan", "Eceabat", "Ezine", "Gelibolu", "Gökçeada", "Lapseki", "Merkez", "Yenice"],
    "18": ["Atkaracalar", "Bayramören", "Çerkeş", "Eldivan", "Ilgaz", "Kızılırmak", "Korgun", "Kurşunlu", "Merkez", "Orta", "Şabanözü", "Yapraklı"],
    "19": ["Alaca", "Bayat", "Boğazkale", "Dodurga", "İskilip", "Kargı", "Laçin", "Mecitözü", "Merkez", "Oğuzlar", "Ortaköy", "Osmancık", "Sungurlu", "Uğurludağ"],
    "20": ["Acıpayam", "Babadağ", "Baklan", "Bekilli", "Beyağaç", "Bozkurt", "Buldan", "Çal", "Çameli", "Çardak", "Çivril", "Güney", "Honaz", "Kale", "Merkezefendi", "Pamukkale", "Sarayköy", "Serinhisar", "Tavas"],
    "21": ["Bağlar", "Bismil", "Çermik", "Çınar", "Çüngüş", "Dicle", "Eğil", "Ergani", "Hani", "Hazro", "Kayapınar", "Kocaköy", "Kulp", "Lice", "Silvan", "Sur", "Yenişehir"],
    "22": ["Enez", "Havsa", "İpsala", "Keşan", "Lalapaşa", "Meriç", "Merkez", "Süloğlu", "Uzunköprü"],
    "23": ["Ağın", "Alacakaya", "Arıcak", "Baskil", "Karakoçan", "Keban", "Kovancılar", "Maden", "Merkez", "Palu", "Sivrice"],
    "24": ["Çayırlı", "İliç", "Kemah", "Kemaliye", "Merkez", "Otlukbeli", "Refahiye", "Tercan", "Üzümlü"],
    "25": ["Aşkale", "Aziziye", "Çat", "Hınıs", "Horasan", "İspir", "Karaçoban", "Karayazı", "Köprüköy", "Narman", "Oltu", "Olur", "Palandöken", "Pasinler", "Pazaryolu", "Şenkaya", "Tekman", "Tortum", "Uzundere", "Yakutiye"],
    "26": ["Alpu", "Beylikova", "Çifteler", "Günyüzü", "Han", "İnönü", "Mahmudiye", "Mihalgazi", "Mihalıççık", "Odunpazarı", "Sarıcakaya", "Seyitgazi", "Sivrihisar", "Tepebaşı"],
    "27": ["Araban", "İslahiye", "Karkamış", "Nizip", "Nurdağı", "Oğuzeli", "Şahinbey", "Şehitkâmil", "Yavuzeli"],
    "28": ["Alucra", "Bulancak", "Çamoluk", "Çanakçı", "Dereli", "Doğankent", "Espiye", "Eynesil", "Görele", "Güce", "Keşap", "Merkez", "Piraziz", "Şebinkarahisar", "Tirebolu", "Yağlıdere"],
    "29": ["Kelkit", "Köse", "Kürtün", "Merkez", "Şiran", "Torul"],
    "30": ["Çukurca", "Derecik", "Merkez", "Şemdinli", "Yüksekova"],
    "31": ["Altınözü", "Antakya", "Arsuz", "Belen", "Defne", "Dörtyol", "Erzin", "Hassa", "İskenderun", "Kırıkhan", "Kumlu", "Payas", "Reyhanlı", "Samandağ", "Yayladağı"],
    "32": ["Aksu", "Atabey", "Eğirdir", "Gelendost", "Gönen", "Keçiborlu", "Merkez", "Senirkent", "Sütçüler", "Şarkikaraağaç", "Uluborlu", "Yalvaç", "Yenişarbademli"],
    "33": ["Akdeniz", "Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli", "Gülnar", "Mezitli", "Mut", "Silifke", "Tarsus", "Toroslar", "Yenişehir"],
    "34": ["Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü", "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt", "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane", "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla", "Ümraniye", "Üsküdar", "Zeytinburnu"],
    "35": ["Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova", "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe", "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz", "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar", "Selçuk", "Tire", "Torbalı", "Urla"],
    "36": ["Akyaka", "Arpaçay", "Digor", "Kağızman", "Merkez", "Sarıkamış", "Selim", "Susuz"],
    "37": ["Abana", "Ağlı", "Araç", "Azdavay", "Bozkurt", "Cide", "Çatalzeytin", "Daday", "Devrekani", "Doğanyurt", "Hanönü", "İhsangazi", "İnebolu", "Küre", "Merkez", "Pınarbaşı", "Seydiler", "Şenpazar", "Taşköprü", "Tosya"],
    "38": ["Akkışla", "Bünyan", "Develi", "Felahiye", "Hacılar", "İncesu", "Kocasinan", "Melikgazi", "Özvatan", "Pınarbaşı", "Sarıoğlan", "Sarız", "Talas", "Tomarza", "Yahyalı", "Yeşilhisar"],
    "39": ["Babaeski", "Demirköy", "Kofçaz", "Lüleburgaz", "Merkez", "Pehlivanköy", "Pınarhisar", "Vize"],
    "40": ["Akçakent", "Akpınar", "Boztepe", "Çiçekdağı", "Kaman", "Merkez", "Mucur"],
    "41": ["Başiskele", "Çayırova", "Darıca", "Derince", "Dilovası", "Gebze", "Gölcük", "İzmit", "Kandıra", "Karamürsel", "Kartepe", "Körfez"],
    "42": ["Ahırlı", "Akören", "Akşehir", "Altınekin", "Beyşehir", "Bozkır", "Cihanbeyli", "Çeltik", "Çumra", "Derbent", "Derebucak", "Doğanhisar", "Emirgazi", "Ereğli", "Güneysınır", "Hadım", "Halkapınar", "Hüyük", "Ilgın", "Kadınhanı", "Karapınar", "Karatay", "Kulu", "Meram", "Sarayönü", "Selçuklu", "Seydişehir", "Taşkent", "Tuzlukçu", "Yalıhüyük", "Yunak"],
    "43": ["Altıntaş", "Aslanapa", "Çavdarhisar", "Domaniç", "Dumlupınar", "Emet", "Gediz", "Hisarcık", "Merkez", "Pazarlar", "Simav", "Şaphane", "Tavşanlı"],
    "44": ["Akçadağ", "Arapgir", "Arguvan", "Battalgazi", "Darende", "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazıhan", "Yeşilyurt"],
    "45": ["Ahmetli", "Akhisar", "Alaşehir", "Demirci", "Gölmarmara", "Gördes", "Kırkağaç", "Köprübaşı", "Kula", "Salihli", "Sarıgöl", "Saruhanlı", "Selendi", "Soma", "Şehzadeler", "Turgutlu", "Yunusemre"],
    "46": ["Afşin", "Andırın", "Çağlayancerit", "Dulkadiroğlu", "Ekinözü", "Elbistan", "Göksun", "Nurhak", "Onikişubat", "Pazarcık", "Türkoğlu"],
    "47": ["Artuklu", "Dargeçit", "Derik", "Kızıltepe", "Mazıdağı", "Midyat", "Nusaybin", "Ömerli", "Savur", "Yeşilli"],
    "48": ["Bodrum", "Dalaman", "Datça", "Fethiye", "Kavaklıdere", "Köyceğiz", "Marmaris", "Menteşe", "Milas", "Ortaca", "Seydikemer", "Ula", "Yatağan"],
    "49": ["Bulanık", "Hasköy", "Korkut", "Malazgirt", "Merkez", "Varto"],
    "50": ["Acıgöl", "Avanos", "Derinkuyu", "Gülşehir", "Hacıbektaş", "Kozaklı", "Merkez", "Ürgüp"],
    "51": ["Altunhisar", "Bor", "Çamardı", "Çiftlik", "Merkez", "Ulukışla"],
    "52": ["Akkuş", "Altınordu", "Aybastı", "Çamaş", "Çatalpınar", "Çaybaşı", "Fatsa", "Gölköy", "Gülyalı", "Gürgentepe", "İkizce", "Kabadüz", "Kabataş", "Korgan", "Kumru", "Mesudiye", "Perşembe", "Ulubey", "Ünye"],
    "53": ["Ardeşen", "Çamlıhemşin", "Çayeli", "Derepazarı", "Fındıklı", "Güneysu", "Hemşin", "İkizdere", "İyidere", "Kalkandere", "Merkez", "Pazar"],
    "54": ["Adapazarı", "Akyazı", "Arifiye", "Erenler", "Ferizli", "Geyve", "Hendek", "Karapürçek", "Karasu", "Kaynarca", "Kocaali", "Pamukova", "Sapanca", "Serdivan", "Söğütlü", "Taraklı"],
    "55": ["Alaçam", "Asarcık", "Atakum", "Ayvacık", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım", "Kavak", "Ladik", "Salıpazarı", "Tekkeköy", "Terme", "Vezirköprü", "Yakakent"],
    "56": ["Baykan", "Eruh", "Kurtalan", "Merkez", "Pervari", "Şirvan", "Tillo"],
    "57": ["Ayancık", "Boyabat", "Dikmen", "Durağan", "Erfelek", "Gerze", "Merkez", "Saraydüzü", "Türkeli"],
    "58": ["Akıncılar", "Altınyayla", "Divriği", "Doğanşar", "Gemerek", "Gölova", "Gürün", "Hafik", "İmranlı", "Kangal", "Koyulhisar", "Merkez", "Suşehri", "Şarkışla", "Ulaş", "Yıldızeli", "Zara"],
    "59": ["Çerkezköy", "Çorlu", "Ergene", "Hayrabolu", "Kapaklı", "Malkara", "Marmaraereğlisi", "Muratlı", "Saray", "Süleymanpaşa", "Şarköy"],
    "60": ["Almus", "Artova", "Başçiftlik", "Erbaa", "Merkez", "Niksar", "Pazar", "Reşadiye", "Sulusaray", "Turhal", "Yeşilyurt", "Zile"],
    "61": ["Akçaabat", "Araklı", "Arsin", "Beşikdüzü", "Çarşıbaşı", "Çaykara", "Dernekpazarı", "Düzköy", "Hayrat", "Köprübaşı", "Maçka", "Of", "Ortahisar", "Sürmene", "Şalpazarı", "Tonya", "Vakfıkebir", "Yomra"],
    "62": ["Çemişgezek", "Hozat", "Mazgirt", "Merkez", "Nazımiye", "Ovacık", "Pertek", "Pülümür"],
    "63": ["Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Eyyübiye", "Halfeti", "Haliliye", "Harran", "Hilvan", "Karaköprü", "Siverek", "Suruç", "Viranşehir"],
    "64": ["Banaz", "Eşme", "Karahallı", "Merkez", "Sivaslı", "Ulubey"],
    "65": ["Bahçesaray", "Başkale", "Çaldıran", "Çatak", "Edremit", "Erciş", "Gevaş", "Gürpınar", "İpekyolu", "Muradiye", "Özalp", "Saray", "Tuşba"],
    "66": ["Akdağmadeni", "Aydıncık", "Boğazlıyan", "Çandır", "Çayıralan", "Çekerek", "Kadışehri", "Merkez", "Saraykent", "Sarıkaya", "Sorgun", "Şefaatli", "Yenifakılı", "Yerköy"],
    "67": ["Alaplı", "Çaycuma", "Devrek", "Ereğli", "Gökçebey", "Kilimli", "Kozlu", "Merkez"],
    "68": ["Ağaçören", "Eskil", "Gülağaç", "Güzelyurt", "Merkez", "Ortaköy", "Sarıyahşi"],
    "69": ["Aydıntepe", "Demirözü", "Merkez"],
    "70": ["Ayrancı", "Başyayla", "Ermenek", "Kazımkarabekir", "Merkez", "Sarıveliler"],
    "71": ["Bahşılı", "Balışeyh", "Çelebi", "Delice", "Karakeçili", "Keskin", "Merkez", "Sulakyurt", "Yahşihan"],
    "72": ["Beşiri", "Gercüş", "Hasankeyf", "Kozluk", "Merkez", "Sason"],
    "73": ["Beytüşşebap", "Cizre", "Güçlükonak", "İdil", "Merkez", "Silopi", "Uludere"],
    "74": ["Amasra", "Kurucaşile", "Merkez", "Ulus"],
    "75": ["Çıldır", "Damal", "Göle", "Hanak", "Merkez", "Posof"],
    "76": ["Aralık", "Karakoyunlu", "Merkez", "Tuzluca"],
    "77": ["Altınova", "Armutlu", "Çınarcık", "Çiftlikköy", "Merkez", "Termal"],
    "78": ["Eflani", "Eskipazar", "Merkez", "Ovacık", "Safranbolu", "Yenice"],
    "79": ["Elbeyli", "Merkez", "Musabeyli", "Polateli"],
    "80": ["Bahçe", "Düziçi", "Hasanbeyli", "Kadirli", "Merkez", "Sumbas", "Toprakkale"],
    "81": ["Akçakoca", "Cumayeri", "Çilimli", "Gölyaka", "Gümüşova", "Kaynaşlı", "Merkez", "Yığılca"],
}


async def seed_sample_districts(db):
    """Seed real districts for each province using actual Turkish district names."""
    logger.info("Seeding real districts for all 81 provinces...")

    # Get all provinces
    result = await db.execute(select(Province))
    provinces = list(result.scalars().all())

    if not provinces:
        logger.error("No provinces found!")
        return 0, 0

    created = 0

    for province in provinces:
        district_names = TURKEY_DISTRICTS.get(province.code, [])
        if not district_names:
            logger.warning(f"No district data for province code {province.code}, skipping.")
            continue

        # Find the province coordinates from TURKEY_PROVINCES list
        province_data = next(
            (p for p in TURKEY_PROVINCES if p[0] == province.code), None
        )
        if province_data:
            base_lon, base_lat = province_data[3], province_data[4]
        else:
            base_lon, base_lat = 35.0, 39.0

        for i, district_name in enumerate(district_names):
            district_code = f"{province.code}{str(i+1).zfill(2)}"

            # Check if exists
            result = await db.execute(select(District).where(District.code == district_code))
            if result.scalar_one_or_none():
                continue

            # Create near province center with small offset
            lon_offset = random.uniform(-0.3, 0.3)
            lat_offset = random.uniform(-0.3, 0.3)

            centroid_geom = from_shape(Point(base_lon + lon_offset, base_lat + lat_offset), srid=4326)
            district_geom = await create_mock_polygon(base_lon + lon_offset, base_lat + lat_offset, 0.1)

            num_districts = len(district_names)
            district = District(
                id=uuid.uuid4(),
                province_id=province.id,
                code=district_code,
                name=district_name,
                population=int(province.population / num_districts) if province.population else 10000,
                area_km2=1000.0,
                geom=district_geom,
                centroid=centroid_geom,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(district)
            created += 1

        if (provinces.index(province) + 1) % 10 == 0:
            await db.commit()
            logger.info(f"   Progress: {provinces.index(province) + 1}/81 provinces processed...")

    await db.commit()
    logger.info(f"Districts: {created} created")
    return created, 0


async def main():
    """Main seeding function"""
    logger.info("=" * 70)
    logger.info("🚀 TURKEY GEOGRAPHIC DATA SEEDING")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        # Current state
        province_count = await db.execute(select(func.count(Province.id)))
        district_count = await db.execute(select(func.count(District.id)))

        logger.info(f"📊 Current state:")
        logger.info(f"   Provinces: {province_count.scalar()}")
        logger.info(f"   Districts: {district_count.scalar()}")
        logger.info("")

        # Seed provinces
        try:
            p_created, p_updated = await seed_provinces(db)
            logger.info("")
        except Exception as e:
            logger.error(f"❌ Province seeding failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Seed districts
        try:
            d_created, d_updated = await seed_sample_districts(db)
            logger.info("")
        except Exception as e:
            logger.error(f"❌ District seeding failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Final count
        province_count = await db.execute(select(func.count(Province.id)))
        district_count = await db.execute(select(func.count(District.id)))

        logger.info("=" * 70)
        logger.info("✅ SEEDING COMPLETED!")
        logger.info(f"   Provinces: {province_count.scalar()} total (Turkey has 81)")
        logger.info(f"   Districts: {district_count.scalar()} total (Sample data)")
        logger.info("=" * 70)
        logger.info("")
        logger.info("💡 Next steps:")
        logger.info("   1. Restart the backend server to clear caches")
        logger.info("   2. Test GEOINT endpoints with a keyword")
        logger.info("   3. Run: POST /api/v1/geoint/calculate/{keyword_id}")
        logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
