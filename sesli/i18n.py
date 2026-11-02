"""UI text in English and Turkish. The choice is saved in %APPDATA%/Sesli/settings.json."""
import json, os

from paths import DATA
SETTINGS = os.path.join(DATA, 'settings.json')
LANGS = (('en', 'English'), ('tr', 'Türkçe'))


def load_settings():
    try:
        return json.load(open(SETTINGS, encoding='utf-8'))
    except Exception:
        return {}


def save_setting(key, value):
    os.makedirs(DATA, exist_ok=True)
    s = load_settings()
    s[key] = value
    json.dump(s, open(SETTINGS, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


_lang = load_settings().get('lang')


def lang():
    return _lang


def set_lang(code):
    global _lang
    _lang = code
    save_setting('lang', code)


def T(key, **kw):
    s = STR.get(_lang or 'en', STR['en']).get(key) or STR['en'][key]
    return s.format(**kw) if kw else s


STR = {
    'en': {
        'choose_lang': 'Choose your language',
        'language': 'Language',
        'microphone': 'Microphone',
        'your_mic': 'Your mic',
        'discord_hears': 'What Discord hears',
        'proc_on': 'Processing: ON',
        'proc_off': 'Processing: OFF (raw mic)',
        'run_setup': 'Run setup',
        'test_mic': 'Test my mic',
        'noise_removal': 'Noise removal',
        'strong': 'Strong',
        'gentle': 'Gentle',
        'discord_help': 'In Discord → Voice & Video: Input device = "CABLE Output (VB-Audio Virtual Cable)". '
                        'Turn OFF Noise Suppression, Echo Cancellation and Automatic Gain Control. '
                        'Closing this window stops your mic in Discord.',
        'cable_title': 'One-time step: install VB-Cable',
        'cable_why': 'Sesli sends your cleaned-up voice into a free "virtual cable" called VB-Cable. '
                     'Discord (or any app) then uses that cable as its microphone.',
        'cable_1': '1.  Click "Download VB-Cable" and download the Windows driver pack (a .zip).',
        'cable_2': '2.  Unzip it. Right-click VBCABLE_Setup_x64.exe → Run as administrator → Install Driver.',
        'cable_3': '3.  Restart your PC, then open Sesli again.',
        'cable_dl': 'Download VB-Cable',
        'check_again': 'Check again',
        'recording_test': 'Recording — talk like you would on Discord… {s} s',
        'playing_back': 'Playing back what Discord would hear… (on your speakers/headphones)',
        'cant_play': 'Could not play back: {err}',
        'test_done': 'That’s how you sound. Click "Test my mic" to try again.',
        'not_running': 'Not running',
        'live': 'Live',
        'live_off': 'Live — processing off',
        'set_up': 'Set up for this mic.',
        'not_set_up': 'Not set up yet — click Run setup.',
        'busy': '  Your PC is very busy — audio may stutter.',
        'delay': '{cal}  Delay ≈ {ms} ms.{busy}',
        'clip_knob': 'Clipping! Turn the gain knob down.',
        'clip_auto': 'Clipping! Run setup again.',
        'err_nomic': 'No microphone found.',
        'setup_title': 'Sesli — setup',
        'intro_h': 'Let’s set up your mic',
        'intro_p1': 'Sit the way you normally sit when you play. I’ll measure three short things: silence, '
                    'normal talking, and a loud moment. Each one starts only when you click "I’m ready". '
                    'Then I’ll tell you exactly where to put the mic and how to set the gain.',
        'intro_p2': 'If you don’t want to move the mic, tick the box — I’ll get the best sound from where you are.',
        'lock': 'Lock my distance (I’m comfortable here — just set the gain)',
        'knob_q': 'Is there a GAIN knob on your mic or audio interface?',
        'knob_yes': 'Yes (an audio interface like Focusrite or Behringer UMC, or a knob on the mic)',
        'knob_no': 'No (USB mic or headset without a knob) — I’ll set the level for you',
        'start': 'Start',
        'ready': 'I’m ready',
        'ready_hint': 'Click "I’m ready" (or press Enter) when you are.',
        'recording_in': 'Starting in {n}…',
        'recording_left': 'Recording — {s} s left',
        'ph_silence': 'Stay silent',
        'ph_silence_i': 'Don’t talk, don’t type. I’m measuring the room noise.',
        'ph_talk': 'Talk normally',
        'ph_talk_i': 'Read this out loud, like you talk on Discord:',
        'ph_loud': 'Now be LOUD',
        'ph_loud_i': 'Like an exciting moment in a game — loud, but don’t scream into the mic. '
                     'Keep it up until the timer ends.',
        'check_h': 'Quick check',
        'plan_h': 'Here’s the plan',
        'snr_great': 'very clean', 'snr_ok': 'OK', 'snr_bad': 'noisy',
        'plan_now': 'Right now your voice is {snr} dB above the room noise ({word}).',
        'plan_clip': '  Your gain is clipping on loud moments.',
        'dist_hint': 'about {pct}% of your current distance (e.g. 20 cm → {cm} cm)',
        'plan_closer': '1. Move the mic closer: {hint}. I’ll guide you live.',
        'plan_back': '1. Move the mic a bit further away ({hint}) — it’s close enough to sound boomy.',
        'plan_keep': '1. Distance: keep it where it is.',
        'plan_gain': '2. Set the gain — I’ll tell you up or down while you talk.',
        'plan_cal': '3. A short check, then 20 seconds of reading so I can tune the sound to your voice.',
        'q_great': 'Expected quality: great.',
        'q_good': 'Expected quality: good.',
        'q_ok': 'Expected quality: OK — at this distance the noise remover has to work harder, so there’s a small quality hit.',
        'go': 'Go',
        'keep_talking': 'Keep talking normally the whole time (read anything, or count).',
        'start_talking': 'Start talking…',
        'hold': 'Hold it there…',
        'mic_max': 'Your mic is at its maximum level. Move it closer to your mouth.',
        'move_h': 'Move the mic',
        'm_closer': 'Closer… slowly',
        'm_too_far_back': 'A little too far — come back a bit',
        'm_too_close': 'Too close — back off a little',
        'm_further': 'Further away… slowly',
        'm_spot': 'That’s the spot. Stay there.',
        'm_lock_here': 'I can’t go further — lock this distance',
        'm_aim': 'Aim for {hint}. Point the back of the mic at your PC/laptop fan.',
        'gain_h': 'Set the gain',
        'g_up': 'Turn the gain knob UP slowly',
        'g_up_lot': 'Turn the gain knob UP (quite a bit)',
        'g_down': 'Turn the gain knob DOWN slowly',
        'g_down_lot': 'Turn the gain knob DOWN (quite a bit)',
        'g_perfect': 'Perfect. Stop turning.',
        'g_where': 'Use the GAIN knob for your mic, on your audio interface or on the mic. Small turns.',
        'auto_h': 'Setting your mic level',
        'auto_adj': 'Keep talking — I’m adjusting the level',
        'auto_ok': 'Perfect.',
        'auto_note': 'No need to touch anything.',
        'still_clip_h': 'Still clipping on loud moments',
        'still_clip_p': 'Let’s take the gain down a little more.',
        'ok': 'OK',
        'cal_h': 'Last step: read this out loud',
        'cal_p': 'Normal voice, like on Discord. I’m tuning the sound to your voice (20 seconds).',
        'done_h': 'All set',
        'done_p': 'Your voice is about {snr} dB above the room noise. Tone matched to the target within '
                  '{err} dB (was {before} dB off).',
        'done_p2': 'Leave the gain knob where it is. If you move the mic or change rooms, run setup again.',
        'fail_h': 'Couldn’t finish tuning',
        'fail_p': 'I didn’t hear enough talking ({err}). Run setup again and keep reading the whole time.',
        'close': 'Close',
        'tune_btn': 'Tune by ear',
        'tone_label': 'Tone: {t}',
        'tone_default': 'default',
        'tone_reset': 'Reset tone',
        'tune_title': 'Sesli \u2014 tune by ear',
        'tune_h': 'Tune by ear',
        'tune_intro': 'I record 10 seconds of you, then you pick what sounds best \u2014 blind, a few options at '
                      'a time. First we find a direction, then fine-tune. At most 14 choices. Talk like you do on Discord.',
        'tune_pick': 'Which one sounds best?',
        'tune_pair': 'Which sounds better?',
        'tune_check': 'Final check: which do you prefer?',
        'tune_step': 'Choice {n} of at most {m}  \u00b7  keys 1\u20134 switch, Space pauses',
        'tune_loop_hint': 'Drag on the waveform to loop a part \u00b7 click to jump \u00b7 double-click to clear',
        'tune_choose': '✓ {l}',
        'tune_mypick': 'Best:',
        'tune_cant': 'Can\u2019t tell',
        'tune_pause': 'Pause',
        'tune_play': 'Play',
        'tune_habit': 'Letters are shuffled every time \u2014 take your time and listen to all of them.',
        'tune_done_h': 'Done',
        'tw_clear': 'clearer', 'tw_soft': 'softer', 'tw_warm': 'warmer / deeper', 'tw_light': 'lighter',
        'tw_airy': 'airier', 'tw_dark': 'darker', 'tw_none': 'close to the original',
        'tune_res_tuned': 'Your sound: {sound}. In the blind final check you preferred it over the original.',
        'tune_applied': 'Applied \u2014 Discord hears this now. You can undo it with "Reset tone".',
        'tune_res_original': 'In the blind final check you preferred the ORIGINAL, so I kept it. '
                             'Your ears already like the default sound.',
        'tune_res_mixed': 'Your sound: {sound}. The final check was mixed \u2014 the difference to the original is small. '
                          'Which do you want to keep?',
        'tune_use': 'Use the tuned sound',
        'tune_keep': 'Keep the original',
        'read_text': 'Hello, this is a microphone test. I’m speaking in my normal voice, the way I always do. '
                     'The quick brown fox jumps over the lazy dog. Last night we played games with friends and '
                     'stayed up until two. In the morning I made coffee, but the milk had run out, so I drank it '
                     'black. Six slippery snails slid slowly seaward. Peter Piper picked a peck of pickled peppers. '
                     'We still haven’t decided what to do this weekend; maybe we’ll go to the beach.',
    },
    'tr': {
        'choose_lang': 'Dilini seç',
        'language': 'Dil',
        'microphone': 'Mikrofon',
        'your_mic': 'Mikrofonun',
        'discord_hears': 'Discord’un duyduğu',
        'proc_on': 'İşleme: AÇIK',
        'proc_off': 'İşleme: KAPALI (ham mikrofon)',
        'run_setup': 'Kurulumu başlat',
        'test_mic': 'Mikrofonumu test et',
        'noise_removal': 'Gürültü giderme',
        'strong': 'Güçlü',
        'gentle': 'Hafif',
        'discord_help': 'Discord → Ses ve Görüntü: Giriş cihazı = "CABLE Output (VB-Audio Virtual Cable)". '
                        'Gürültü Bastırma, Yankı Engelleme ve Otomatik Kazanç Kontrolü’nü KAPAT. '
                        'Bu pencereyi kapatırsan Discord’da mikrofonun kesilir.',
        'cable_title': 'Bir kerelik adım: VB-Cable kur',
        'cable_why': 'Sesli temizlenmiş sesini VB-Cable adlı ücretsiz bir "sanal kabloya" gönderir. '
                     'Discord (ya da başka bir uygulama) bu kabloyu mikrofon olarak kullanır.',
        'cable_1': '1.  "VB-Cable’ı indir"e tıkla ve Windows sürücü paketini (.zip) indir.',
        'cable_2': '2.  Zip’i aç. VBCABLE_Setup_x64.exe’ye sağ tıkla → Yönetici olarak çalıştır → Install Driver.',
        'cable_3': '3.  Bilgisayarı yeniden başlat, sonra Sesli’yi tekrar aç.',
        'cable_dl': 'VB-Cable’ı indir',
        'check_again': 'Tekrar kontrol et',
        'recording_test': 'Kaydediliyor — Discord’daki gibi konuş… {s} sn',
        'playing_back': 'Discord’un duyacağı ses çalınıyor… (hoparlör/kulaklıktan)',
        'cant_play': 'Çalınamadı: {err}',
        'test_done': 'Sesin böyle duyuluyor. Tekrar denemek için "Mikrofonumu test et"e tıkla.',
        'not_running': 'Çalışmıyor',
        'live': 'Canlı',
        'live_off': 'Canlı — işleme kapalı',
        'set_up': 'Bu mikrofon için ayarlandı.',
        'not_set_up': 'Henüz ayarlanmadı — Kurulumu başlat’a tıkla.',
        'busy': '  Bilgisayarın çok meşgul — ses takılabilir.',
        'delay': '{cal}  Gecikme ≈ {ms} ms.{busy}',
        'clip_knob': 'Patlıyor! Gain düğmesini kıs.',
        'clip_auto': 'Patlıyor! Kurulumu tekrar yap.',
        'err_nomic': 'Mikrofon bulunamadı.',
        'setup_title': 'Sesli — kurulum',
        'intro_h': 'Mikrofonunu ayarlayalım',
        'intro_p1': 'Oyun oynarken nasıl oturuyorsan öyle otur. Üç kısa şey ölçeceğim: sessizlik, normal konuşma '
                    've yüksek ses. Her biri ancak "Hazırım"a tıkladığında başlar. Sonra mikrofonu nereye '
                    'koyacağını ve gain’i nasıl ayarlayacağını tam olarak söyleyeceğim.',
        'intro_p2': 'Mikrofonu oynatmak istemiyorsan kutuyu işaretle — bulunduğun yerden en iyi sesi çıkarırım.',
        'lock': 'Mesafemi sabitle (burada rahatım — sadece gain’i ayarla)',
        'knob_q': 'Mikrofonunda veya ses kartında GAIN düğmesi var mı?',
        'knob_yes': 'Evet (Focusrite, Behringer UMC gibi bir ses kartı ya da mikrofonda bir düğme)',
        'knob_no': 'Hayır (düğmesiz USB mikrofon ya da kulaklık) — seviyeyi ben ayarlarım',
        'start': 'Başla',
        'ready': 'Hazırım',
        'ready_hint': 'Hazır olunca "Hazırım"a tıkla (ya da Enter’a bas).',
        'recording_in': '{n}… sonra başlıyor',
        'recording_left': 'Kaydediliyor — {s} sn kaldı',
        'ph_silence': 'Sessiz kal',
        'ph_silence_i': 'Konuşma, klavyeye dokunma. Odanın gürültüsünü ölçüyorum.',
        'ph_talk': 'Normal konuş',
        'ph_talk_i': 'Bunu Discord’da konuştuğun gibi sesli oku:',
        'ph_loud': 'Şimdi YÜKSEK sesle',
        'ph_loud_i': 'Oyunda heyecanlı bir an gibi — yüksek, ama mikrofona bağırma. Süre bitene kadar devam et.',
        'check_h': 'Kısa kontrol',
        'plan_h': 'Plan şöyle',
        'snr_great': 'çok temiz', 'snr_ok': 'idare eder', 'snr_bad': 'gürültülü',
        'plan_now': 'Şu an sesin oda gürültüsünün {snr} dB üstünde ({word}).',
        'plan_clip': '  Yüksek seste gain patlıyor.',
        'dist_hint': 'şu anki mesafenin yaklaşık %{pct}’i (ör. 20 cm → {cm} cm)',
        'plan_closer': '1. Mikrofonu yaklaştır: {hint}. Canlı yönlendireceğim.',
        'plan_back': '1. Mikrofonu biraz uzaklaştır ({hint}) — çok yakın, ses boğuk çıkıyor.',
        'plan_keep': '1. Mesafe: olduğu yerde kalsın.',
        'plan_gain': '2. Gain’i ayarla — sen konuşurken aç/kıs diye söyleyeceğim.',
        'plan_cal': '3. Kısa bir kontrol, sonra sesini ayarlamam için 20 saniye okuma.',
        'q_great': 'Beklenen kalite: çok iyi.',
        'q_good': 'Beklenen kalite: iyi.',
        'q_ok': 'Beklenen kalite: idare eder — bu mesafede gürültü giderici daha çok çalışıyor, kalitede biraz kayıp olur.',
        'go': 'Devam',
        'keep_talking': 'Bu sırada normal konuşmaya devam et (herhangi bir şey oku ya da say).',
        'start_talking': 'Konuşmaya başla…',
        'hold': 'Orada kal…',
        'mic_max': 'Mikrofonun en yüksek seviyede. Ağzına daha yaklaştır.',
        'move_h': 'Mikrofonu taşı',
        'm_closer': 'Yaklaş… yavaşça',
        'm_too_far_back': 'Biraz fazla uzaklaştın — biraz geri gel',
        'm_too_close': 'Çok yakın — biraz geri çekil',
        'm_further': 'Uzaklaş… yavaşça',
        'm_spot': 'İşte orası. Orada kal.',
        'm_lock_here': 'Daha fazla yaklaşamam — bu mesafeyi sabitle',
        'm_aim': 'Hedef: {hint}. Mikrofonun arkasını bilgisayar/laptop fanına çevir.',
        'gain_h': 'Gain’i ayarla',
        'g_up': 'Gain düğmesini yavaşça AÇ',
        'g_up_lot': 'Gain düğmesini AÇ (epey)',
        'g_down': 'Gain düğmesini yavaşça KIS',
        'g_down_lot': 'Gain düğmesini KIS (epey)',
        'g_perfect': 'Mükemmel. Çevirmeyi bırak.',
        'g_where': 'Ses kartındaki (ya da mikrofondaki) GAIN düğmesini kullan. Küçük dokunuşlarla.',
        'auto_h': 'Mikrofon seviyen ayarlanıyor',
        'auto_adj': 'Konuşmaya devam et — seviyeyi ayarlıyorum',
        'auto_ok': 'Mükemmel.',
        'auto_note': 'Hiçbir şeye dokunmana gerek yok.',
        'still_clip_h': 'Yüksek seste hâlâ patlıyor',
        'still_clip_p': 'Gain’i biraz daha kısalım.',
        'ok': 'Tamam',
        'cal_h': 'Son adım: bunu sesli oku',
        'cal_p': 'Normal sesle, Discord’daki gibi. Sesi sana göre ayarlıyorum (20 saniye).',
        'done_h': 'Hazır',
        'done_p': 'Sesin oda gürültüsünün yaklaşık {snr} dB üstünde. Ton hedefe {err} dB yakınlığa getirildi '
                  '(önce {before} dB uzaktı).',
        'done_p2': 'Gain düğmesini olduğu yerde bırak. Mikrofonu taşırsan ya da oda değiştirirsen kurulumu tekrar yap.',
        'fail_h': 'Ayar tamamlanamadı',
        'fail_p': 'Yeterince konuşma duyamadım ({err}). Kurulumu tekrar yap ve süre boyunca okumaya devam et.',
        'close': 'Kapat',
        'tune_btn': 'Kulağımla ayarla',
        'tone_label': 'Ton: {t}',
        'tone_default': 'varsayılan',
        'tone_reset': 'Tonu sıfırla',
        'tune_title': 'Sesli \u2014 kulakla ayar',
        'tune_h': 'Kulağınla ayarla',
        'tune_intro': '10 saniye sesini kaydediyorum, sonra en iyi geleni seçiyorsun \u2014 kör test, her seferinde '
                      'birkaç seçenek. Önce yönü buluyoruz, sonra ince ayar. En fazla 14 seçim. Discord\u2019daki gibi konuş.',
        'tune_pick': 'Hangisi en iyi?',
        'tune_pair': 'Hangisi daha iyi?',
        'tune_check': 'Son kontrol: hangisini tercih ediyorsun?',
        'tune_step': 'Seçim {n} / en fazla {m}  \u00b7  1\u20134 tuşları değiştirir, Boşluk durdurur',
        'tune_loop_hint': 'Bir kısmı döngüye almak için dalga üzerinde sürükle \u00b7 tıkla: atla \u00b7 çift tıkla: temizle',
        'tune_choose': '✓ {l}',
        'tune_mypick': 'En iyisi:',
        'tune_cant': 'Fark yok',
        'tune_pause': 'Durdur',
        'tune_play': 'Çal',
        'tune_habit': 'Harfler her seferinde karışıyor \u2014 acele etme, hepsini dinle.',
        'tune_done_h': 'Bitti',
        'tw_clear': 'daha net', 'tw_soft': 'daha yumuşak', 'tw_warm': 'daha sıcak / tok', 'tw_light': 'daha ince',
        'tw_airy': 'daha ferah', 'tw_dark': 'daha koyu', 'tw_none': 'orijinale yakın',
        'tune_res_tuned': 'Senin sesin: {sound}. Son kör kontrolde bunu orijinale tercih ettin.',
        'tune_applied': 'Uygulandı \u2014 Discord artık bunu duyuyor. "Tonu sıfırla" ile geri alabilirsin.',
        'tune_res_original': 'Son kör kontrolde ORİJİNALİ tercih ettin, onu bıraktım. Kulağın zaten varsayılan sesi seviyor.',
        'tune_res_mixed': 'Senin sesin: {sound}. Son kontrol karışık çıktı \u2014 orijinalle fark küçük. Hangisini tutalım?',
        'tune_use': 'Ayarlı sesi kullan',
        'tune_keep': 'Orijinali tut',
        'read_text': 'Merhaba, bu bir mikrofon test kaydı. Şu an normal sesimle, her zamanki gibi konuşuyorum. '
                     'Pijamalı hasta yağız şoföre çabucak güvendi. Dün akşam arkadaşlarla oyun oynadık, saat ikiye '
                     'kadar uyumadık. Sabah kalktığımda kahve yaptım ama süt bitmişti, mecburen sade içtim. '
                     'Sessiz sokakta sisli bir sabah, saat sekizi seksen geçiyordu. Pazartesi patron bana para verdi, '
                     'ben de bir paket pide aldım. Hafta sonu ne yapacağımıza daha karar vermedik, belki sahile gideriz.',
    },
}
