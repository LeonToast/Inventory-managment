# Smart Lagring – arbetsflöden
## Systemets delar

```mermaid
flowchart LR
    User[Användare] --> Browser[Webbläsare]
    Browser --> Frontend[Vue 3 + TypeScript<br/>Vite :5173]
    Frontend -->|HTTP + Bearer-token| API[FastAPI<br/>Uvicorn :8000]
    API --> Auth{Autentisering<br/>och rollkontroll}
    Auth -->|Tillåten begäran| Router[API-router]
    Router --> Mongo[(MongoDB)]
    Mongo --> Router
    Router -->|JSON-svar| Frontend
    Frontend --> Browser
```

## Inloggning och behörighet

```mermaid
flowchart TD
    Start[Öppna Smart Lagring] --> Login[Ange e-post och lösenord]
    Login --> Verify[POST /login]
    Verify --> Valid{Uppgifter giltiga?}
    Valid -->|Nej| Error[Visa inloggningsfel]
    Error --> Login
    Valid -->|Ja| Token[Backend utfärdar signerad token]
    Token --> Role{Användarroll}
    Role -->|Admin| AdminMenu[Visa adminfunktioner]
    Role -->|Worker| WorkerMenu[Visa arbetsfunktioner]
    AdminMenu --> AdminRequest[Adminbegäran]
    WorkerMenu --> UserRequest[Inloggad användarbegäran]
    AdminRequest --> RequireAdmin{Är token giltig<br/>och rollen Admin?}
    UserRequest --> RequireUser{Är token giltig?}
    RequireAdmin -->|Ja| ProtectedAction[Utför administratörsåtgärd]
    RequireAdmin -->|Nej| Forbidden[HTTP 401 eller 403]
    RequireUser -->|Ja| ReadAction[Utför tillåten åtgärd]
    RequireUser -->|Nej| Forbidden
```

## Aktivera och använda tvåfaktorsautentisering (2FA)

```mermaid
flowchart TD
    Signup[Personen fyller i kontoansökan] --> Enable{Aktivera 2FA?}
    Enable -->|Nej| Submit[Skicka kontoansökan]
    Enable -->|Ja| Setup[Begär 2FA-inställning<br/>från backend]
    Setup --> QR[Visa QR-kod och reservnyckel]
    QR --> App[Skanna med authenticator-app]
    App --> InitialCode[Ange aktuell sexsiffrig kod]
    InitialCode --> VerifySetup{Verifierar koden?}
    VerifySetup -->|Nej| SetupError[Visa fel och begär ny kod]
    SetupError --> InitialCode
    VerifySetup -->|Ja| Submit2FA[Skicka ansökan med 2FA aktiverat]
    Submit --> Pending[Väntar på adminens godkännande]
    Submit2FA --> Pending
    Pending --> Approved{Godkänner admin ansökan?}
    Approved -->|Nej| Rejected[Ansökan avslås]
    Approved -->|Ja| Account[Worker-konto skapas]
    Account --> Login[Logga in med e-post och lösenord]
    Login --> Has2FA{Är 2FA aktiverat<br/>på kontot?}
    Has2FA -->|Nej| Token[Utfärda inloggningstoken]
    Has2FA -->|Ja| NeedCode[Be om authenticator-kod]
    NeedCode --> Code[Ange aktuell sexsiffrig kod]
    Code --> VerifyCode{Är koden giltig?}
    VerifyCode -->|Nej| LoginError[Visa felmeddelande]
    LoginError --> NeedCode
    VerifyCode -->|Ja| Token
```

2FA konfigureras som en del av kontoansökan och aktiveras först när ansökan godkänns. QR-koden/nyckeln kopplas till en authenticator-app; den aktuella koden kontrolleras vid registrering och vid framtida inloggningar.

> **Utvecklingskonto:** den lokala inloggningen `admin@dev.local` har en särskild utvecklingsväg i backend som utfärdar token utan att kräva lösenord eller 2FA. Den vägen är inte exempel på säker produktionskonfiguration.

## Material och utgående leverans

```mermaid
flowchart TD
    Open[Öppna Materiel eller Leverans] --> Load[Hämta material från API]
    Load --> Choose{Välj åtgärd}
    Choose -->|Registrera material| MaterialForm[Admin fyller i materialformulär]
    MaterialForm --> MaterialCheck[Kontrollera lager, SKU, antal och mått]
    MaterialCheck --> MaterialValid{Giltiga uppgifter<br/>och kapacitet?}
    MaterialValid -->|Nej| ShowError[Visa fel, behåll formuläret]
    MaterialValid -->|Ja| SaveMaterial[Spara material i MongoDB]
    Choose -->|Skapa leverans| DeliveryForm[Admin väljer kund, artikel och antal]
    DeliveryForm --> StockCheck[Kontrollera oskadat lagersaldo]
    StockCheck --> Enough{Tillräckligt saldo?}
    Enough -->|Nej| ShowError
    Enough -->|Ja| Decrement[Minska saldo]
    Decrement --> SaveDelivery[Spara leverans]
    SaveDelivery --> Audit[Registrera aktivitet]
    SaveDelivery --> SaveOK{Kunde leveransen sparas?}
    SaveOK -->|Nej| Restore[Återställ lagersaldo]
    SaveOK -->|Ja| Refresh[Uppdatera leverans och översikt]
    Choose -->|Avbryt skickad leverans| Cancel[Återför leveransens antal]
    Cancel --> Audit
```

## Lagerutrymme

```mermaid
flowchart LR
    Material[Materialets längd, bredd och antal] --> Area[Beräkna golvyta<br/>längd × bredd × antal ÷ 10 000]
    Area --> Measured[Summera uppmätt yta per lager]
    Capacity[Lagrets kapacitet i m²] --> Percent[Beräkna uppmätt andel]
    Measured --> Percent
    Missing{Finns material<br/>utan mått?}
    Measured --> Missing
    Missing -->|Ja| Minimum[Visa uppmätt yta som minimum<br/>och visa antal material utan mått]
    Missing -->|Nej| Complete[Visa fullständig uppmätt andel]
```

Stapling räknas inte med. Om mått saknas ska procenten inte tolkas som en fullständig beräkning.

## Skapa och visa rapport

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#ffffff","primaryTextColor":"#111827","primaryBorderColor":"#475569","lineColor":"#475569","secondaryColor":"#ffffff","tertiaryColor":"#ffffff","textColor":"#111827","edgeLabelBackground":"#ffffff","fontFamily":"Segoe UI, Arial, sans-serif"}}}%%
flowchart TD
    Admin["1. Administratör<br/>Väljer rapporttyp, lager och datumperiod"] --> Validate["2. Rapportsidan<br/>Kontrollerar datumintervallet"]
    Validate -->|Giltiga datum| Create["3. Frontend skickar POST /reports<br/>med Bearer-token"]
    Validate -->|Slutdatum före startdatum| DateError["Visa datumfel<br/>och behåll formuläret"]
    DateError --> Admin

    Create --> Auth{"4. FastAPI<br/>Giltig token, adminroll<br/>och rapportuppgifter?"}
    Auth -->|Nej| AuthError["Visa behörighets- eller valideringsfel"]
    Auth -->|Ja| ReadSource["5. Läs rapportunderlag"]

    ReadSource --> Source{"Rapporttyp"}
    Source -->|Lager, saldo eller skador| Materials[("MongoDB<br/>material + warehouse")]
    Source -->|Leveranser| Deliveries[("MongoDB<br/>deliveries")]
    Source -->|Kapacitet| Capacity[("MongoDB<br/>materialmått + warehouse")]
    Source -->|Aktiviteter| Activity[("MongoDB<br/>audit_logs")]

    Materials --> Build["6. FastAPI bygger<br/>sammanfattning och rapportposter"]
    Deliveries --> Build
    Capacity --> Build
    Activity --> Build
    Build --> Save[("7. Spara rapport<br/>generated_reports")]
    Save --> Return["8. API returnerar rapport"]
    Return --> Archive["9. Rapportarkivet visar<br/>sammanfattning och innehåll"]

    Archive --> Open["Öppna rapportinnehåll"]
    Open --> Fetch["GET /reports<br/>med Bearer-token"]
    Fetch --> Saved[("Hämta sparade rapporter<br/>från MongoDB")]
    Saved --> Display["Visa rapporter i arkivet"]

    classDef userStep fill:#e0f2fe,stroke:#0369a1,color:#111827,stroke-width:1.5px
    classDef frontendStep fill:#dcfce7,stroke:#15803d,color:#111827,stroke-width:1.5px
    classDef backendStep fill:#ede9fe,stroke:#6d28d9,color:#111827,stroke-width:1.5px
    classDef databaseStep fill:#fef3c7,stroke:#a16207,color:#111827,stroke-width:1.5px
    classDef errorStep fill:#fee2e2,stroke:#b91c1c,color:#111827,stroke-width:1.5px

    class Admin userStep
    class Validate,Create,Archive,Open,Display frontendStep
    class Auth,ReadSource,Source,Build,Return,Fetch backendStep
    class Materials,Deliveries,Capacity,Activity,Save,Saved databaseStep
    class DateError,AuthError errorStep
```

Lageröversikt, lågt lagersaldo, skador och lagerutrymme visar nuläget. Datumperioden används för leverans- och aktivitetsrapporter.

## Ändra en funktion

```mermaid
flowchart LR
    Requirement[Bestäm önskat beteende] --> Vue[Uppdatera Vue-vy eller formulär]
    Vue --> Request[Skicka API-begäran]
    Request --> Model[Validera data i Pydantic-modell]
    Model --> Role[Kontrollera roll i FastAPI-router]
    Role --> Database[Läs eller uppdatera MongoDB]
    Database --> Response[Returnera JSON eller tydligt fel]
    Response --> UI[Visa resultat eller felmeddelande]
    UI --> Verify[Testa frontend, API och relevanta kantfall]
```

## Relaterad projektguide

Se [WORKFLOW.md](./WORKFLOW.md) för instruktioner om att starta projektet, detaljer för varje vy och felsökning.
