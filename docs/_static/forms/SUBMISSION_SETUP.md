# Configurazione del portale SEASTRONG

Il portale raccoglie i sei tipi di rilievo e carica i dati nel Drive condiviso istituzionale. Il sito puo essere pubblicato su GitHub Pages. Ogni collaboratore accede con un account Google e deve avere il permesso di aggiungere file alla cartella di destinazione. Tutti i file del portale sono accanto ai PDF; i PDF originali restano disponibili per il lavoro sul campo.

## Aprire la prova locale

Su Mac, aprire `Open SEASTRONG Form.command`. Su Windows, aprire `Open SEASTRONG Form.bat`. E necessario Python 3. Si apre `http://localhost:8000/`; lasciare aperta la finestra di avvio. In alternativa, dalla cartella dei moduli eseguire `python3 preview_submission.py`.

Per collegare Google, usare questo indirizzo locale: l'apertura diretta di `index.html` dal Finder non permette ai moduli JavaScript e all'autorizzazione Google di funzionare correttamente.

Prima provare un piccolo rilievo identificabile come test. Premere **Sign in with Google** e accedere con l'account istituzionale. Il sito prova a collegarsi direttamente alla cartella SEASTRONG configurata. Se questa non e ancora autorizzata all'app, Google mostra una conferma limitata alla cartella **Survey submissions**, con la navigazione laterale nascosta. Confermarla per concedere all'app l'accesso tramite l'ambito limitato `drive.file`. Ai collegamenti successivi, quando Google permette gia l'accesso, il selettore non viene aperto. Il sito verifica che la cartella sia in un Drive condiviso e che sia possibile aggiungere file.

Compilare i dati, selezionare pochi file e inviare. Aprire la cartella risultante e controllare che siano presenti JSON, CSV, PDF e originali. Una prova locale esegue veri caricamenti solo dopo **Submit to Shared Drive**. La conferma finale viene mostrata dopo la verifica di ID, cartella di appartenenza e dimensione dei file.

## Impostazioni Google

La configurazione pubblica del browser si trova in `submission-config.js`. Contiene ID client OAuth, chiave API limitata per sito/API, numero progetto e ID della cartella. Questi identificatori non sostituiscono il consenso Google e i permessi sul Drive. Non inserire password, segreti client OAuth, chiavi di account di servizio o token di accesso in questo file o nel repository.

Nel progetto Google Cloud **SEASTRONG Field Portal**:

1. In **API e servizi → Libreria**, abilitare **Google Drive API** e **Google Picker API**.
2. In **Piattaforma Google Auth → Branding**, impostare nome app e indirizzi di assistenza/contatto.
3. In **Pubblico**, scegliere **Esterno** se partecipano altri enti. Durante la prova mantenere lo stato di test e aggiungere gli account di prova in **Utenti di test**. Aggiungere altri utenti di test prima di invitarli a usare la versione non pubblicata.
4. In **Accesso ai dati → Aggiungi o rimuovi ambiti**, selezionare `https://www.googleapis.com/auth/drive.file`.
5. Creare un client OAuth di tipo **Applicazione web**. Le **Origini JavaScript autorizzate** sono `https://alerovere.github.io` e `http://localhost:8000`. Non aggiungere il percorso del repository. Per il flusso del browser usato qui non servono URI di reindirizzamento.
6. Limitare la chiave API ai siti `https://alerovere.github.io/*`, `http://localhost:8000/*` e `https://docs.google.com/*`. Limitare le API a **Google Picker API** e **Google Drive API**. Il dominio docs.google.com e usato dalla finestra di scelta di Google.
7. Copiare il **Numero progetto** da **IAM e amministrazione → Impostazioni** nel campo `googleProjectNumber`.

Collegamenti diretti: [Branding](https://console.cloud.google.com/auth/branding?hl=it), [Pubblico](https://console.cloud.google.com/auth/audience?hl=it), [Accesso ai dati](https://console.cloud.google.com/auth/scopes?hl=it). Controllare sempre il progetto selezionato in alto.

La documentazione di riferimento e la [guida Google al consenso OAuth](https://developers.google.com/workspace/guides/configure-oauth-consent?hl=it) e la [guida Google Picker](https://developers.google.com/workspace/drive/picker/guides/web-picker-sample). Prima di estendere l'accesso al consorzio, completare gli eventuali requisiti di pubblicazione/verifica richiesti da Google. Lo stato **Esterno** non rende pubblici i dati e non concede automaticamente permessi sul Drive.

## Accesso iniziale al portale

Il modulo e l'elenco dei record vengono mostrati soltanto dopo l'accesso Google e la verifica del permesso di aggiungere file alla cartella configurata. **Lock portal** nasconde il modulo e rimuove la sessione dalla memoria; anche la scadenza della sessione riporta alla schermata iniziale. I draft locali sono separati per account Google. Un vecchio draft senza autore non viene aperto automaticamente: puo essere importato dopo l'accesso. I record gia inviati restano disponibili da **My records**.

Questo controllo dell'interfaccia non rende privati i file statici di GitHub Pages o il codice del repository pubblico. I record sul Drive restano soggetti ai permessi Google.

## Permessi dei collaboratori

Condividere la cartella di destinazione o il Drive con gli account autorizzati, usando almeno il ruolo che permette di aggiungere file. Le politiche dell'ateneo possono limitare gli account esterni. Un indirizzo Gmail non e obbligatorio: un account Google puo usare anche un indirizzo istituzionale esistente.

Se un collaboratore vede la pagina ma non riesce a caricare, verificare separatamente account di prova OAuth, autorizzazione dell'app e permesso sulla cartella. Il client non crea condivisioni e non modifica i permessi. La verifica effettiva del ruolo avviene all'apertura della cartella tramite Drive API. Il selettore di Google opera con l'account della persona che ha effettuato l'accesso; non mostra agli altri i Drive del responsabile del progetto. I metodi [`setFileIds`](https://developers.google.com/workspace/drive/picker/reference/picker.docsview.setfileids) e [`NAV_HIDDEN`](https://developers.google.com/workspace/drive/picker/reference/picker.feature) limitano la prima conferma alla cartella configurata. Il codice rifiuta comunque una selezione con un ID diverso.

## Organizzazione delle consegne

La cartella di destinazione contiene area, corridoio, survey ID e una cartella distinta per ogni record:

```text
Survey submissions/
  Belize/
    C1/
      BZ140327C1reef/
        BZ140327C1reef_record_<submission-id>/
          BZ140327C1reef_submission.json
          BZ140327C1reef_file_manifest.json
          BZ140327C1reef_field_report.pdf
          BZ140327C1reef_targets.csv
          BZ140327C1reef_depth_profile.csv
          BZ140327C1reef_camA/
          BZ140327C1reef_camB/
          BZ140327C1reef_field_sheets/
```

Il campo facoltativo **Corridor name** conserva il nome locale (per esempio Mangrove Bay) nel JSON, nei CSV, nel rapporto PDF e nelle revisioni. Il codice C1-C6 e l'identificativo automatico restano invariati. Le nuove tabelle CSV includono `corridor_name`; rimane possibile importare i precedenti modelli senza questa colonna.

I nomi dei file originali ricevono il prefisso del survey ID, senza modificare i contenuti. Il manifest conserva il percorso originale, il nome salvato, la dimensione e l'ID del file su Drive. Le sottocartelle selezionate vengono mantenute. Per un secondo rilievo dello stesso tipo nello stesso corridoio/giorno, scegliere il suffisso B, C o D. Il servizio Google permette nomi duplicati: il portale distingue ogni consegna con un ID univoco e rifiuta una gerarchia gia ambigua; non garantisce l'unicita globale del nome in caso di creazione simultanea da computer diversi.

Per completare o correggere un rilievo gia consegnato, aprire **My records**, individuare il record e usare **Edit**. E disponibile anche **Edit this record** nella conferma finale. Il modulo recupera i dati salvati su Drive e prepara una nuova versione. Questo vale anche per deployment e recupero dei sensori. Ogni versione ha una propria cartella e una propria consegna JSON, PDF e CSV. Le foto e gli altri originali delle versioni precedenti vengono verificati e riutilizzati tramite collegamenti; non occorre selezionarli o caricarli di nuovo. Il nuovo file `*_file_links.csv` contiene i collegamenti Drive degli originali, compresi quelli delle versioni precedenti. Se si rimuove un file dal nuovo record, la copia gia archiviata nella versione precedente resta presente.

## Consultare e modificare i propri record

Dopo il collegamento con Google, aprire **My records**. L'elenco viene letto da Drive e non dipende dal browser o dal computer usato per l'invio. Mostra l'ultima versione di ciascun record; **Show earlier versions** permette di consultare lo storico. **View** apre i metadati, le misure, le note e i collegamenti ai file. **Edit** recupera i dati nel modulo. Dopo le correzioni, seguire i quattro passaggi e inviare: viene aggiunta una nuova versione, con autore Google, numero versione e riferimento alla precedente. L'identificativo del rilievo resta fisso; per un altro luogo, corridoio o data si avvia un nuovo rilievo.

L'autore viene associato all'identificativo dell'account restituito da Google, separatamente dal campo testuale **Filled in by**. Il portale filtra l'elenco e l'editor per quell'account. Questo filtro dell'applicazione non sostituisce i permessi del Drive condiviso: cio che un collaboratore puo fare direttamente da Google Drive continua a dipendere dalle autorizzazioni istituzionali.

I record della prima versione non avevano un autore Google registrato nel JSON. Quelli precedenti e ancora accessibili vengono inclusi soltanto se Google li indica come modificati l'ultima volta dall'account collegato, e sono riconoscibili come **Earlier format**. Questo riscontro non prova chi li aveva creati originariamente; la distinzione rimane esplicita. Una loro modifica produce una nuova versione attribuita all'account corrente e conserva la precedente. I draft locali ed esportati della versione 1.0 restano importabili.

Un pacchetto indicato come incompleto puo essere consultato nell'elenco, ma va ripreso dal draft del browser originale o dal draft esportato: il JSON iniziale sul Drive potrebbe non contenere gli ultimi avanzamenti di un caricamento interrotto. Il portale non inventa i file gia caricati e non modifica un record incompleto come se fosse una consegna terminata.

## Draft e interruzioni

Il browser salva misure, note e l'elenco dei file in `localStorage`. **Download draft** permette di conservarne una copia o spostarla su un altro computer. Gli originali e i token Google non vengono salvati nel draft. Una pagina privata/in incognito, la cancellazione dei dati del browser o un browser diverso possono non avere il draft: mantenere la copia esportata e gli originali sul computer.

Gli upload sono divisi in blocchi. Dopo un'interruzione, mantenere aperta la pagina e riprendere. Se la pagina viene ricaricata, selezionare nuovamente gli stessi file, nella stessa categoria, con gli stessi percorsi e date di modifica. Gli originali gia confermati sono verificati su Drive e saltati; un file parziale viene ripreso nella sessione aperta o riscritto nello stesso ID riservato. Se l'accesso Google scade, riconnettersi e riprendere.

Il record JSON resta `uploading` fino al salvataggio e alla verifica di tutti gli originali, CSV, rapporto e manifest. Solo l'ultima scrittura lo imposta a `complete`. Il completamento del pacchetto non dimostra che tutte le misure sul campo siano presenti: le informazioni mancanti e lo stato del rilievo restano espliciti. La verifica dei file usa dimensione e appartenenza alla cartella, non il confronto crittografico dell'intero contenuto.

Le tabelle derivano dagli attuali generatori PDF. I metodi A/B/C delle mangrovie mostrano le proprie tabelle; le nove quadrature e le misure dei cinque germogli per quadrato delle fanerogame hanno tabelle separate. Per importare CSV, scaricare prima il modello della tabella selezionata; l'importazione sostituisce quella tabella dopo conferma. I CSV esportati proteggono i campi testuali che potrebbero essere interpretati come formule. Il rapporto PDF usa un font standard: eventuali caratteri non supportati vengono sostituiti con `?`; il JSON e i CSV mantengono il testo originale.

## Pubblicazione su GitHub Pages

Il codice rimane in `docs/_static/forms/` insieme ai PDF. Per non introdurre file di configurazione fuori da questa cartella e non interferire con Read the Docs, pubblicare una copia statica su un ramo dedicato `gh-pages`. Il ramo non deve sostituire un sito GitHub Pages gia esistente.

Il comando `python3 publish_submission.py --prepare` prepara una copia locale della pagina e dei PDF e stampa la cartella di anteprima. Non pubblica. Dopo aver controllato la copia, `python3 publish_submission.py --publish` crea o aggiorna soltanto il ramo `gh-pages` del repository configurato come origin. Se il ramo esistente appartiene a un altro sito, lo script si ferma. Questa pubblicazione non esegue il commit o il push delle modifiche al ramo di sviluppo; conservare anche quelle nel normale flusso Git del progetto.

In GitHub aprire **Settings → Pages**, scegliere **Deploy from a branch**, poi **gh-pages** e **/(root)**. Il sito sara disponibile all'indirizzo `https://alerovere.github.io/seastrong-field-tools/`. La copia pubblicata ha `.nojekyll` alla radice, quindi non subisce l'esclusione Jekyll delle cartelle con underscore. Il sito puo essere pubblico; Google mantiene protetto l'accesso ai dati.

Per aggiornare la pagina, cambiare i file in questa cartella, provare localmente e ripubblicare. Il portale usa `pdf-lib` 1.17.1 incluso localmente con la sua licenza MIT. Non servono build Node o pacchetti esterni per usare la pagina; le sole librerie caricate da Google sono quelle di autorizzazione e Picker. Vengono preparate all'apertura della pagina; l'accesso all'account comincia soltanto premendo il pulsante di collegamento.

## Costi

La prima versione richiede account Google e carica direttamente nel Drive: non usa Cloud Run, Cloudflare o un server applicativo aggiuntivo. GitHub Pages e disponibile nel piano gratuito per repository pubblici. Lo spazio consumato dai dati e quello del Workspace istituzionale. L'uso standard di Drive API non ha costi aggiuntivi entro i limiti pubblicati; le quote possono interrompere o limitare i caricamenti. Verificare lo spazio disponibile e le [quote Google Drive aggiornate](https://developers.google.com/workspace/drive/api/guides/limits). Non occorre attivare una prova Cloud o aggiungere una carta per questa architettura.

## Controlli prima dell'uso sul campo

Provare l'accesso da un secondo account autorizzato, il caricamento di una piccola consegna di ogni tipo, una cartella con foto e un'interruzione/ripresa. Controllare i rapporti e le colonne CSV rispetto ai protocolli. Provare anche un account senza permessi per verificare che venga rifiutato. La connessione e i caricamenti reali nel tenant istituzionale richiedono questa prova: le verifiche automatiche locali usano una simulazione di Google e non attestano le politiche effettive dell'ateneo.
