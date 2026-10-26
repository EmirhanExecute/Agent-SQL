"""UI strings (Turkish / English)."""

STRINGS = {
    "tr": {
        "title": "SQL Ajanı",
        "language": "Dil / Language",
        "database": "Veritabanı",
        "db_small": "Northwind (küçük örnek)",
        "db_full": "Northwind (tam)",
        "safety": "Yalnızca SELECT çalışır; salt okunur bağlantı, 100 satır sınırı, 5 sn zaman aşımı, "
                  "telefon/adres gibi kolonlar gizli.",
        "clear": "Sohbeti temizle",
        "examples_title": "Örnek sorular",
        "examples": [
            "En çok sipariş veren 5 müşteri kim?",
            "Ürün kategorisine göre toplam gelir",
            "1996 yılında aylık sipariş sayısı",
            "İspanya'ya gönderilen siparişleri hiç işlemeyen çalışanlar kimler?",
        ],
        "chat_input": "Veritabanına bir soru sorun",
        "spinner": "Sorgu hazırlanıyor...",
        "used_sql": "Kullanılan SQL",
        "no_result": "Sonuç bulunamadı.",
        "error": "Bir hata oluştu: {err}",
        "meta": "{attempts} deneme · {tokens} token · {rows} satır",
        "truncated": "{n}+ satır, ilk {n} gösteriliyor",
        "chart_min_size": "Grafik için en az 2 satır ve 2 sütun gerekir.",
        "chart_first_col": "İlk sütun kategori ya da tarih değil.",
        "chart_no_numeric": "Sayısal sütun yok.",
        "chart_too_many": "Çok fazla kategori var; tabloyu kullanın.",
    },
    "en": {
        "title": "SQL Agent",
        "language": "Dil / Language",
        "database": "Database",
        "db_small": "Northwind (small sample)",
        "db_full": "Northwind (full)",
        "safety": "Only SELECT runs: read-only connection, 100-row limit, 5 s timeout, "
                  "phone/address-type columns are hidden.",
        "clear": "Clear chat",
        "examples_title": "Example questions",
        "examples": [
            "Who are the top 5 customers by number of orders?",
            "Total revenue per product category",
            "Monthly number of orders in 1996",
            "Which employees never handled an order shipped to Spain?",
        ],
        "chat_input": "Ask the database a question",
        "spinner": "Preparing the query...",
        "used_sql": "SQL used",
        "no_result": "No result found.",
        "error": "An error occurred: {err}",
        "meta": "{attempts} attempt(s) · {tokens} tokens · {rows} rows",
        "truncated": "{n}+ rows, showing the first {n}",
        "chart_min_size": "A chart needs at least 2 rows and 2 columns.",
        "chart_first_col": "The first column is neither a category nor a date.",
        "chart_no_numeric": "There is no numeric column.",
        "chart_too_many": "Too many categories; use the table.",
    },
}

LANGUAGES = {"Türkçe": "tr", "English": "en"}
