import requests
from datetime import datetime, timezone

# --- CONFIGURATION ---
# Si le script tourne sur le même serveur que CTFd (Docker), laisse localhost:8000
# Sinon, mets l'URL publique de ta plateforme (ex: "https://ctf.monclub.fr")
CTFD_URL = "https://ctf.pony7.fr/api/v1"  

# Allez dans Profil -> Settings -> Access Tokens pour générer cette clé
API_TOKEN = ""

# Le chemin où Nginx va lire le fichier HTML pour l'afficher sur le web
OUTPUT_PATH = "/var/www/ctf-event/index.html"

# Fenêtre de temps du CTF de l'année (en UTC pour éviter les décalages horaires)
CTF_START = datetime(2025, 10, 11, 18, 0, 0, tzinfo=timezone.utc) # Début : 22 Mai 2026 à 18h UTC
CTF_END   = datetime(2025, 10, 22, 18, 0, 0, tzinfo=timezone.utc) # Fin : 24 Mai 2026 à 18h UTC

# Les IDs des challenges créés spécifiquement pour ce CTF annuel
EVENT_CHALLENGE_IDS = [101, 102, 103, 104, 105] 
# ---------------------

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def build_scoreboard():
    # 1. Récupération de toutes les résolutions via l'API
    response = requests.get(f"{CTFD_URL}/solves", headers=HEADERS)
    if response.status_code != 200:
        print(f"[-] Erreur API (Code {response.status_code}). Vérifie ton Token ou l'URL.")
        return
    
    all_solves = response.json().get('data', [])
    scoreboard = {}

    # 2. Filtrage des données
    for solve in all_solves:
        chall_id = solve['challenge_id']
        
        # On ignore le challenge s'il ne fait pas partie du CTF de cette année
        if chall_id not in EVENT_CHALLENGE_IDS:
            continue
            
        # CTFd renvoie les dates au format ISO (ex: "2026-05-23T14:32:10.000000Z")
        solve_time = datetime.fromisoformat(solve['date'].replace('Z', '+00:00'))

        # On garde uniquement si la résolution a eu lieu PENDANT l'événement
        if CTF_START <= solve_time <= CTF_END:
            username = solve['user']['name']
            points = solve['challenge']['value']
            
            if username not in scoreboard:
                scoreboard[username] = {"score": 0, "last_solve": solve_time}
            
            scoreboard[username]["score"] += points
            # Gestion du "Tie-break" (le premier qui atteint le score a l'avantage)
            if solve_time > scoreboard[username]["last_solve"]:
                scoreboard[username]["last_solve"] = solve_time

    # Tri : Plus haut score d'abord. Si égalité, le plus rapide à avoir validé gagne.
    sorted_ranking = sorted(scoreboard.items(), key=lambda x: (-x[1]['score'], x[1]['last_solve']))

    # 3. Génération de la page HTML (Design sombre avec TailwindCSS)
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classement Live - CTF Événement</title>
    <!-- Actualise la page automatiquement toutes les 30 secondes -->
    <meta http-equiv="refresh" content="30"> 
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans antialiased min-h-screen flex flex-col items-center py-12 px-4">
    <div class="w-full max-w-4xl">
        <header class="text-center mb-12">
            <h1 class="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                🏆 Classement Officiel du CTF Annuel
            </h1>
            <p class="text-slate-400 mt-2 text-sm">Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Heure Serveur)</p>
        </header>

        <main class="bg-slate-800 rounded-xl shadow-2xl border border-slate-700 overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-700 text-slate-300 font-semibold text-sm tracking-wider uppercase border-b border-slate-600">
                        <th class="py-4 px-6 w-20 text-center">Rang</th>
                        <th class="py-4 px-6">Joueur / Équipe</th>
                        <th class="py-4 px-6 text-right w-36">Score Total</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-700">
    """

    for rank, (user, data) in enumerate(sorted_ranking, start=1):
        # Émojis stylés pour le TOP 3
        rank_display = str(rank)
        if rank == 1: rank_display = "🥇"
        elif rank == 2: rank_display = "🥈"
        elif rank == 3: rank_display = "🥉"

        html_content += f"""
                    <tr class="hover:bg-slate-750/50 transition-colors">
                        <td class="py-4 px-6 text-center font-bold text-lg">{rank_display}</td>
                        <td class="py-4 px-6 font-medium text-slate-200">{user}</td>
                        <td class="py-4 px-6 text-right font-mono font-bold text-cyan-400 text-lg">{data['score']} pts</td>
                    </tr>
        """
    
    if not sorted_ranking:
        html_content += """
                    <tr>
                        <td colspan="3" class="py-12 text-center text-slate-400">Aucun flag validé pour le moment. Bon courage !</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </main>
    </div>
</body>
</html>
    """

    # Écriture du fichier sur le disque
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Scoreboard mis à jour avec succès à {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    build_scoreboard()
