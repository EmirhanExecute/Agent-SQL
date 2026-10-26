# Benchmark: ayar karşılaştırması (ablasyon)

Her ayar bir öncekine **bir yardım daha ekler** (kümülatif). Ayarlar yalnızca *kalite* özelliklerini açıp kapatır; güvenlik
katmanları (SQL doğrulayıcı, salt okunur bağlantı, 100 satır sınırı, zaman aşımı, hassas kolon gizleme) ve
"cevaplanamaz / netleştir" kuralı **her ayarda açıktır**. Uygulama (arayüz ve CLI) artık yalnızca `full` ayarıyla çalışır;
diğer ayarlar bu karşılaştırmayı yeniden üretmek için `eval/run_eval.py` içinde durur.

## Ayarlar

| Ayar | Eklediği özellik | Kısaca |
|---|---|---|
| `baseline` | Hiçbiri | Model yalnızca tüm tabloların şemasını ve soruyu görür. Tek deneme. |
| `fewshot` | `few_shot` | Soruya en çok benzeyen 3 çözülmüş örnek (soru + doğru SQL) prompta eklenir. |
| `repair` | `repair` | SQL hata verirse ya da güvenlik doğrulayıcı reddederse hata mesajı modele geri gider, en çok 3 deneme. |
| `values` | `value_dict` + `value_linking` | Kategorik kolonların değer listeleri ve terimler sözlüğü şemaya eklenir; sorudaki yazım hatalı değer gerçek değere bağlanır ("Seafod" → `Seafood`). |
| `tables` | `table_select` | Model önce hangi tabloların gerektiğini seçer; yalnızca onların şeması gönderilir (ara tablolar otomatik eklenir). |
| `full` | `memory` | Takip sorusu, önceki sorular da kullanılarak bağımsız bir soruya çevrilir. **Uygulamanın kullandığı ayar.** |

## Düzenek

- Veri: Northwind (`northwind_small.db`: 100 sipariş; `northwind_full.db`: 830 sipariş).
- Model: `gemini-3.5-flash-lite` (embedding: `gemini-embedding-001`).
- Soru seti: `eval/questions.yaml`, toplam 90 soru. 36 `train` (few-shot havuzu), **54 `test`** (yalnızca bunlar ölçülür).
  Test seti: 8 kolay, 21 orta, 18 zor SQL sorusu (toplam 47) ve 4 cevaplanamaz, 3 belirsiz soru.
- Metrik: *execution accuracy*. Üretilen SQL'in sonucu gold SQL'in sonucuyla aynı mı (satır ve kolon sırasından bağımsız,
  küçük yuvarlama farkları toleranslı). Cevaplanamaz/belirsiz sorularda doğru davranış, SQL çalıştırmadan reddetmek ya da
  netleştirme sorusu sormaktır.
- Yeniden üretmek için:

```bash
python eval/run_eval.py --db small --configs baseline,fewshot,repair,values,tables
python eval/run_eval.py --db full  --configs baseline,fewshot,repair,values,tables
```

## Sonuçlar (54 test sorusu, tek koşu)

Doğruluk (%95 güven aralığı), soru başına ortalama token ve deneme sayısı:

| Ayar | Küçük DB | Tam DB | Token/soru (küçük) | Deneme/soru (küçük) |
|---|---|---|---|---|
| `baseline` | %89 (48/54; %78-95) | %87 (47/54; %76-94) | 2398 | 1.00 |
| `fewshot` | %94 (51/54; %85-98) | %89 (48/54; %78-95) | 2523 | 1.00 |
| `repair` | %94 (51/54; %85-98) | %91 (49/54; %80-96) | 2523 | 1.00 |
| `values` | %96 (52/54; %87-99) | %94 (51/54; %85-98) | 3694 | 1.02 |
| `tables` | %96 (52/54; %87-99) | %96 (52/54; %87-99) | 1493 | 1.04 |
| `full` | ölçülmedi | ölçülmedi | | |

Soru türüne göre doğru sayısı (tam DB):

| Ayar | Kolay (8) | Orta (21) | Zor (18) | Cevaplanamaz (4) | Belirsiz (3) |
|---|---|---|---|---|---|
| `baseline` | 7 | 20 | 13 | 4 | 3 |
| `fewshot` | 7 | 19 | 16 | 3 | 3 |
| `repair` | 7 | 20 | 16 | 3 | 3 |
| `values` | 7 | 20 | 17 | 4 | 3 |
| `tables` | 7 | 21 | 17 | 4 | 3 |

Küçük DB'de dağılım: `baseline` 7/20/14/4/3, `fewshot` ve `repair` 7/20/17/4/3, `values` ve `tables` 7/21/17/4/3.

Güvenlik seti (`eval/run_security.py`, zehirli veritabanı, 15 saldırı senaryosu): 15/15 geçti.

## Nasıl okunmalı

- Sıralama beklenen yönde (`baseline` en düşük, `tables` en yüksek), ama güven aralıkları örtüşüyor. Tek koşu olduğu için
  bunlar kesin kanıt değil, yön göstergesi.
- `fewshot` zor sorularda en büyük sıçramayı yaptı (tam DB: 13 → 16).
- `repair` neredeyse hiç tetiklenmedi (deneme/soru ≈ 1.00): model nadiren çalışmayan SQL üretiyor. Etkisi bu soru setiyle
  ölçülebilir değil.
- `values`, değer eşleme sorularında (örneğin `UK`, `Sales Representative`) işe yaradı ama prompt'u büyüttü (2523 → 3694 token).
- `tables`, token'ı yaklaşık yarıya indirdi (3694 → 1493) ama ek bir LLM çağrısı yaptığı için gecikmeyi artırdı.
- `full` ayrıca ölçülmedi: eval soruları tek tek sorulduğundan hafızanın etkisi bu testte görünmez.

## Dikkat edilmesi gerekenler

- **Test seti sonuçlara bakıldıktan sonra iki kez düzeltildi:** iki belirsiz soru ifadesi netleştirildi (hangi kolonların
  istendiği belli değildi) ve sayı karşılaştırması yuvarlama sınır hatasına karşı toleranslı hale getirildi. Düzeltmeler tüm
  ayarlara eşit uygulandı, ama `baseline` bu yüzden ilk koşudaki %77'den %88-89'a çıktı.
- **Tek koşu:** model `temperature` ayarını yok sayıyor, sonuçlar koşudan koşuya biraz değişebilir. LLM yanıtları diske
  cache'lendiği için yeniden koşular aynı sonucu verir; gerçek tekrar için `LLM_CACHE_SALT` değiştirilmelidir.
- **Gecikme sütunu güvenilir değil:** cache'ten gelen çağrıların süresi farklı koşulardan karışıyor, bu yüzden tabloda yok.
- **Few-shot havuzu eval dosyasıyla aynı dosyada** (`train` olarak işaretli sorular); test soruları havuza girmez (testle
  garanti altında).
