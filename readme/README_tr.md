# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Genel Bakış
Bu Home Assistant entegrasyonu, Xsense cihazlarının akıllı ev sistemine entegre edilmesine olanak tanır. [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) tarafından oluşturulan orijinal kod temel alınarak Theo'nun izni ve işbirliği ile yayımlanmıştır.

Theo tarafından resmi bir Home Assistant entegrasyonu sunulana kadar, bu HACS entegrasyonu kullanılacak ve mevcut sorunları çözmek ve yeni özellikler eklemek için düzenli olarak güncellenecektir. Bu entegrasyon, kullanıcıların Xsense cihazlarını Home Assistant'a kolayca entegre etmelerini ve çeşitli otomasyonlar ve izleme amaçlarıyla kullanmalarını sağlar.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Özellikler
- Çeşitli Xsense cihazlarını Home Assistant'a entegre eder.
- Xsense sensör verilerine dayalı otomasyon desteği.
- Aşağıdaki cihaz türleri için destek: ana istasyonlar, duman dedektörleri, karbonmonoksit dedektörleri, ısı alarmları, su sızıntısı dedektörleri ve higrometreler.
- HACS (Home Assistant Community Store) üzerinden kolay kurulum.

## Gereksinimler
- Çalışan bir Home Assistant sunucusu (en son sürüm önerilir).
- Desteklenen cihazlarla birlikte bir Xsense hesabı.
- Entegrasyonun kurulabilmesi için Home Assistant'ta HACS'in yüklü olması gerekmektedir.

## Nasıl Yapılır Videosu
Entegrasyonun kurulumu ve yapılandırılması hakkında detaylı bir rehber için aşağıdaki videoyu izleyebilirsiniz:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Hazırlık
Entegrasyonu kurmadan önce bazı hazırlıklar yapılmalıdır:

- **Xsense uygulamasında ikinci bir hesap oluşturun (Home Assistant kullanımı için)**: Aynı hesaba hem uygulama hem de Home Assistant ile aynı anda giriş yapılamadığından, Home Assistant için ayrı bir hesap kullanmanızı öneririz. Bu şekilde, uygulama ve Home Assistant arasında sürekli olarak oturum açma ve kapama zorunluluğundan kaçınılır. Ek hesap, kesintisiz bir kullanım ve sorunsuz entegrasyon sağlar.

- **Ana hesaptaki desteklenen cihazları Home Assistant hesabıyla paylaşın**: Xsense uygulamasını kullanarak **sadece desteklenen cihazları** yeni oluşturduğunuz hesapla paylaşın. Böylece, entegrasyonu Home Assistant'ta sorunsuz kullanabilir ve cihazları ana hesabınız üzerinden yönetmeye devam edebilirsiniz.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## HACS Üzerinden Kurulum
1. **Home Assistant'ta HACS'i açın**:
   HACS, Home Assistant için önemli bir eklentidir ve özel entegrasyonların kolayca kurulmasına olanak tanır.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Özel depolara gidin**:
   HACS kontrol panelinde ayarlara gidin ve bu depoyu özel kaynak olarak ekleyin.

3. **Depoyu ekleyin**:
   Depo URL'sini girin: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Entegrasyonu indirin ve yükleyin**:
   HACS'te entegrasyonu arayın, indirin ve yükleyin. Kurulum tamamlandıktan sonra Home Assistant arayüzü üzerinden yapılandırma yapılabilir.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Yapılandırma
Kurulumdan sonra entegrasyonu doğru bir şekilde ayarlamak için temel bir yapılandırma gereklidir:
- **Kullanıcı adı ve şifre**: Yeni oluşturduğunuz Xsense hesabının kimlik bilgilerini kullanarak bağlantıyı kurun。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Cihaz görünümü**: Başarılı bir kurulumdan sonra paylaşılan cihazlar Home Assistant'ta kullanılabilir hale gelir ve otomasyonlar için kullanılabilir。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant'ta Görünüm
Başarılı bir kurulum ve yapılandırma sonrasında entegrasyon Home Assistant'ta görünür olacaktır。Cihazlar kontrol panelinde görüntülenebilir ve otomasyonlar, bildirimler ve diğer uygulamalar için kullanılabilir。

![Форум](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Desteklenen Cihazlar
Bu entegrasyon çeşitli Xsense cihazlarını destekler。Aşağıda şu anda onaylanmış ve test edilmiş cihazların bir listesi bulunmaktadır：
- **Ana İstasyon (SBS50)**：Xsense cihazlarının merkezi hub'ı。
- **Isı Alarmı (XH02-M)**：Olağandışı yüksek sıcaklıkları algılar。
- **Karbonmonoksit Dedektörü (XC01-M; XC04-WX)**：Tehlikeli karbonmonoksit konsantrasyonlarını algılar。
- **Duman Dedektörü (XS01-M, WX; XS03-WX; XS0B-MR)**：Erken aşamada duman tespit eder。
- **Karbonmonoksit ve Duman Kombinasyonu Alarmı (SC07-WX; XP0A-MR (kısmen desteklenir))**：Karbonmonoksit ve dumanı algılayan kombinasyon cihazı。
- **Su Sızıntısı Dedektörü (SWS51)**：İstenmeyen yerlerdeki suyu algılar。
- **Higrometre-Termometre (STH51)**：Sıcaklık ve nemi izler。

Bu cihazlar Home Assistant'a entegre edildikten sonra otomasyonlar ve alarmlar oluşturmak için kullanılabilir。

____________________________________________________________

## Otomasyon Örnekleri
Bu entegrasyonla çeşitli otomasyonlar oluşturabilirsiniz。İşte bazı örnekler：

### Örnek 1：Sıcaklık Uyarısı
Xsense termometresinin sıcaklığı çok yüksek olduğunda bir bildirim gönderilir：

```yaml
automation：
  - alias："Xsense Sıcaklık Uyarısı"
    trigger：
      platform：numeric_state
      entity_id：sensor.xsense_temperature
      above：30
    action：
      service：notify.notify
      data：
        message："Sıcaklık 30 dereceyi aştı！"
```

### Örnek 2：Su Sızıntısı Alarmı
Su sızıntısı dedektörü su tespit ettiğinde bir alarm tetiklenir：

```yaml
automation：
  - alias："Su Sızıntısı Alarmı"
    trigger：
      platform：state
      entity_id：binary_sensor.xsense_waterleak
      to："on"
    action：
      service：notify.notify
      data：
        message："Su sızıntısı tespit edildi！"
```

____________________________________________________________

## Yardımınıza İhtiyacımız Var
Bu entegrasyonu daha da geliştirmek ve iyileştirmek için sürekli olarak destek arıyoruz。İşte yardım edebileceğiniz bazı yollar：

1. **Cihaz Testi**：Xsense cihazınız varsa ve bu entegrasyonla uyumlu ise bize bildirin, desteklenen cihazlar listesine ekleyelim。

2. **Desteklenmeyen cihazlar hakkında geri bildirim**：Bir cihaz çalışmıyorsa, bize geri bildirim sağlayın, böylece destek sunabilir veya gelecekteki sürümlere dahil edebiliriz。

3. **Test için cihaz paylaşımı**：Yeni cihazları test etmenin en iyi yolu Xsense uygulaması üzerinden cihazı paylaşmaktır。Bu şekilde mümkün olan en fazla cihazın desteklenmesini sağlayabiliriz。

4. **Topluluk Desteği**：Topluluk tartışmalarına katılın。İster geliştirme önerisi olsun ister diğer kullanıcılara yardımcı olun, her türlü destek memnuniyetle karşılanır！

Tartışmalar ve destek için Discord sunucumuza katılabilir veya Home Assistant forumunu ziyaret edebilirsiniz：

[Discord](https：//discord.gg/5phHHgGb3V)

[Forum](https：//community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
