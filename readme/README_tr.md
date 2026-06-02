# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Genel Bakış
Bu Home Assistant entegrasyonu, X-Sense cihazlarının akıllı ev sistemine entegre edilmesine olanak tanır. [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) tarafından oluşturulan orijinal kod temel alınarak Theo'nun izni ve işbirliği ile yayımlanmıştır.

Bu HACS entegrasyonu, Home Assistant içinde daha geniş X-Sense cihaz desteği isteyen kullanıcılar için aktif olarak sürdürülür. Yeni işlevler, ek cihaz kapsamı ve bildirilen sorunlara yönelik düzeltmelerle düzenli olarak güncellenir.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Özellikler
- Çeşitli X-Sense cihazlarını Home Assistant'a entegre eder.
- X-Sense sensör verilerine dayalı otomasyon desteği.
- Aşağıdaki cihaz türleri için destek: ana istasyonlar, duman dedektörleri, karbonmonoksit dedektörleri, ısı alarmları, su sızıntısı dedektörleri ve higrometreler.
- HACS (Home Assistant Community Store) üzerinden kolay kurulum.

## Gereksinimler
- Çalışan bir Home Assistant sunucusu (en son sürüm önerilir).
- Desteklenen cihazlarla birlikte bir X-Sense hesabı.
- Entegrasyonun kurulabilmesi için Home Assistant'ta HACS'in yüklü olması gerekmektedir.

## Nasıl Yapılır Videosu
Entegrasyonun kurulumu ve yapılandırılması hakkında detaylı bir rehber için aşağıdaki videoyu izleyebilirsiniz:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Hazırlık
Entegrasyonu kurmadan önce bazı hazırlıklar yapılmalıdır:

- **X-Sense uygulamasında ikinci bir hesap oluşturun (Home Assistant kullanımı için)**: Aynı hesaba hem uygulama hem de Home Assistant ile aynı anda giriş yapılamadığından, Home Assistant için ayrı bir hesap kullanmanızı öneririz. Bu şekilde, uygulama ve Home Assistant arasında sürekli olarak oturum açma ve kapama zorunluluğundan kaçınılır. Ek hesap, kesintisiz bir kullanım ve sorunsuz entegrasyon sağlar.

- **Ana hesaptaki desteklenen cihazları Home Assistant hesabıyla paylaşın**: X-Sense uygulamasını kullanarak **sadece desteklenen cihazları** yeni oluşturduğunuz hesapla paylaşın. Böylece, entegrasyonu Home Assistant'ta sorunsuz kullanabilir ve cihazları ana hesabınız üzerinden yönetmeye devam edebilirsiniz.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## HACS Üzerinden Kurulum
1. **Home Assistant'ta HACS'i açın**:
  HACS, Home Assistant için önemli bir eklentidir ve özel entegrasyonların kolayca kurulmasına olanak tanır.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Özel depolara gidin**:
  HACS kontrol panelinde ayarlara gidin ve bu depoyu özel kaynak olarak ekleyin.

3. **Depoyu ekleyin**:
  Depo URL'sini girin: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Entegrasyonu indirin ve yükleyin**:
  HACS'te entegrasyonu arayın, indirin ve yükleyin. Kurulum tamamlandıktan sonra Home Assistant arayüzü üzerinden yapılandırma yapılabilir.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Yapılandırma
Kurulumdan sonra entegrasyonu doğru bir şekilde ayarlamak için temel bir yapılandırma gereklidir:
- **Kullanıcı adı ve şifre**: Yeni oluşturduğunuz X-Sense hesabının kimlik bilgilerini kullanarak bağlantıyı kurun.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Cihaz görünümü**: Başarılı bir kurulumdan sonra paylaşılan cihazlar Home Assistant'ta kullanılabilir hale gelir ve otomasyonlar için kullanılabilir.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant'ta Görünüm
Başarılı bir kurulum ve yapılandırma sonrasında entegrasyon Home Assistant'ta görünür olacaktır. Cihazlar kontrol panelinde görüntülenebilir ve otomasyonlar, bildirimler ve diğer uygulamalar için kullanılabilir.

![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Desteklenen Cihazlar
Bu entegrasyon çeşitli X-Sense cihazlarını destekler. Oluşturulan varlıklar, cihazın ve hesabın bildirdiği veri alanlarına bağlıdır. Onaylanan aileler ve modeller şunları içerir:
- **Baz istasyonu (SBS50)**: X-Sense cihazları için merkezi hub.
- **Isı alarmı (XH02-M)**: Olağandışı yüksek sıcaklıkları algılar.
- **Karbon monoksit dedektörü (XC01-M; XC04-WX)**: Tehlikeli CO yoğunluklarını algılar.
- **Duman dedektörü (XS01-M; XS01-WX; XS03-WX; XS0B-MR ve ilgili RF/iR modelleri)**: Erken duman algılama.
- **CO ve duman kombine dedektörü (SC07-WX; XP0A-MR ve ilgili XP/SC modelleri)**: CO ve dumanı algılar.
- **Su sızıntı dedektörü (SWS51)**: İstenmeyen yerlerde suyu algılar.
- **Higrometre-termometre (STH51, STH0A, STH0B, STH0C)**: Sıcaklık ve nemi izler.
- **Kapı sensörü (SDS0A)** ve **hareket sensörü (SMS0A)**: X-Sense durum bildirdiğinde gösterilir.
- **Kamera (SSC0A, SSC0B)**: Cihaz ve hesap desteklediğinde kamera varlıkları, küçük resimler, canlı yayın URL'leri, durum tanıları ve Android uygulamasına dayalı ayarları sağlar.
- **Diğer istasyon cihazları**: Işık, tuş takımı, posta kutusu, dinleme cihazı, araç yolu alarmı, akıllı teslimat cihazı, kumanda ve radon verileri API desteklenen alanları bildirdiğinde gösterilir.

### Kullanılabilir varlıklar ve eylemler
Entegrasyon yalnızca X-Sense bulutunda, MQTT shadow payload'larında veya Android uygulamasıyla uyumlu kamera API'lerinde gerçekten bulunan alanlar için Home Assistant varlıkları oluşturur. Cihaza bağlı olarak şunları içerebilir:

- Alarm, sessize alma, kullanım ömrü sonu, AC kesintisi, su alarmı, sıcaklık alarmı, şarj, hareket, kapı, kurulu durum, uyarı, hatırlatıcı, ışık, PIR ve tuş takımı durumu için ikili sensörler.
- Pil, RF sinyali, Wi-Fi sinyali, firmware, sıcaklık, nem, CO seviyesi, CO tepe değeri, alarm/konuşma/chirp/hatırlatıcı ses seviyesi, uyarı eşikleri, sessize alma sayaçları, okunabilir zaman damgaları, saat dilimi ve diğer tanılama sensörleri.
- LED ışık, alarm etkinleştirme, devam eden alarm, chirp tonu, hatırlatıcılar, PIR, sunshine/white light, bekleme, tuş takımı sesi, kamera hareket algılama, kayıt, gece görüşü, ses, cooldown, ışık ve kapı zili kontrolleri gibi X-Sense tarafından bildirilen yazılabilir ayarlar için anahtarlar.
- Dil, kayıt çözünürlüğü, codec, anti-flicker oranı, hareket hassasiyeti, video süresi, ses seviyesi, alarm süresi, cooldown, gece eşiği ve kapı zili tuşu gibi desteklenen kamera ayarları için seçimler ve sayı varlıkları.
- X-Sense uygulamasının ilgili modeli desteklediği durumlarda test, sessize alma, yangın tatbikatı ve kamera uyandırma düğmeleri.

Bazı varlıklar tanılama veya yapılandırma ile ilgilidir ve Home Assistant içinde buna göre gruplandırılır. Cihaz belirli bir alanı bildirmezse veya X-Sense uygulaması bu cihaz/hesap için özelliği desteklenmiyor olarak işaretlerse ilgili varlık oluşturulmaz. Cihaz bağlama, kaldırma, paylaşma, hesap, ödeme, firmware güncelleme, SD kart biçimlendirme ve diğer yönetim işlemleri X-Sense uygulamasında kalır.
____________________________________________________________

## Otomasyon Örnekleri
Bu entegrasyonla çeşitli otomasyonlar oluşturabilirsiniz. İşte bazı örnekler:

### Örnek 1: Sıcaklık Uyarısı
X-Sense termometresinin sıcaklığı çok yüksek olduğunda bir bildirim gönderilir:

```yaml
automation:
  - alias: "X-Sense Sıcaklık Uyarısı"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Sıcaklık 30 dereceyi aştı!"
```

### Örnek 2: Su Sızıntısı Alarmı
Su sızıntısı dedektörü su tespit ettiğinde bir alarm tetiklenir:

```yaml
automation:
  - alias: "Su Sızıntısı Alarmı"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Su sızıntısı tespit edildi!"
```

____________________________________________________________

## Yardımınıza İhtiyacımız Var
Bu entegrasyonu daha da geliştirmek ve iyileştirmek için sürekli olarak destek arıyoruz. İşte yardım edebileceğiniz bazı yollar:

1. **Cihaz Testi**: X-Sense cihazınız varsa ve bu entegrasyonla uyumlu ise bize bildirin, desteklenen cihazlar listesine ekleyelim.

2. **Desteklenmeyen cihazlar hakkında geri bildirim**: Bir cihaz çalışmıyorsa, bize geri bildirim sağlayın, böylece destek sunabilir veya gelecekteki sürümlere dahil edebiliriz.

3. **Test için cihaz paylaşımı**: Yeni cihazları test etmenin en iyi yolu X-Sense uygulaması üzerinden cihazı paylaşmaktır. Bu şekilde mümkün olan en fazla cihazın desteklenmesini sağlayabiliriz.

4. **Topluluk Desteği**: Topluluk tartışmalarına katılın. İster geliştirme önerisi olsun ister diğer kullanıcılara yardımcı olun, her türlü destek memnuniyetle karşılanır!

Tartışmalar ve destek için Discord sunucumuza katılabilir veya Home Assistant forumunu ziyaret edebilirsiniz:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Tam Başvuru

### Hesap ve kurulum
- Home Assistant için ayrı bir X-Sense hesabı kullanın.
- Ana hesaptan yalnızca desteklenen cihazları bu hesaba paylaşın.
- Eşleştirme, kaldırma, paylaşma, firmware, hesap, ödeme ve SD kart yönetimi X-Sense uygulamasında kalır.
- Uygulama ile Home Assistant birbirini oturumdan çıkarıyorsa aynı hesabın kullanılmadığını kontrol edin.

### Güncellemeler ve API kullanımı
- Hızlı durum değişiklikleri MQTT shadow mesajlarıyla alınır.
- Bulut istekleri oturum açma, cihaz keşfi, kamera verileri ve durum yenileme için kullanılır.
- Periyodik sorgulama yalnızca canlı güncelleme eksik kaldığında yedek olarak kullanılır.
- Entegrasyon X-Sense API kullanımını gereksiz yere artırmamak için tam cihaz keşfini her güncellemede tekrarlamaz.

### Varlıklar, kameralar ve sorun giderme
- Varlıklar yalnızca X-Sense gerçekten ilgili alanı bildirdiğinde oluşturulur.
- Kamera varlıkları ve kamera kontrolleri yalnızca Android uygulamasıyla uyumlu API, ilgili hesap ve model için destek bildirdiğinde oluşturulur.
- WebRTC yolu Home Assistant içinde kullanılabilir olduğunda, uygun kamera canlı görüntüsü için kullanılabilir.
- Eksik bir değer varsa önce X-Sense uygulamasında aynı değerin görünüp değiştiğini kontrol edin, ardından tanılama çıktısını ve ilgili Home Assistant günlüklerini ekleyin.

## Cihaz ve Varlık Kontrol Listesi

### Ana cihaz aileleri
- SBS50 baz istasyonu, XS duman alarmları, XC CO alarmları, SC/XP birleşik alarmlar, XH ısı alarmları, SWS su kaçağı dedektörleri, STH sıcaklık/nem sensörleri, SDS kapı sensörleri, SMS hareket sensörleri, SSC kameralar ve X-Sense tarafından bildirilen diğer aileler, API desteklenen alanları sağladığında desteklenir.

### Durum alanları
- Alarm, sessize alma, pil, RF/Wi-Fi sinyali, sıcaklık, nem, CO, su, hareket, kapı, ışık, hatırlatıcılar, uyarılar ve okunabilir zaman damgaları yalnızca X-Sense bunları bildirdiğinde görünür.

### Kontroller ve raporlama
- Anahtarlar, seçimler, sayılar ve düğmeler yalnızca cihaz ve hesap tarafından sağlanan yazılabilir ayarlar ve eylemler için oluşturulur.
- İyi bir hata bildirimi kesin modeli, entegrasyon sürümünü, tanılama çıktısını, günlükleri ve değerin X-Sense uygulamasında doğru değişip değişmediğini içerir.
