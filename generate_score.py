import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# Charge les variables du fichier .env local
load_dotenv()

# --- CONFIGURATION ---
CTFD_URL = "https://ctf.pony7.fr/api/v1"
API_TOKEN = os.getenv("CTFD_API_TOKEN")

if not API_TOKEN:
    raise ValueError("Erreur : La variable CTFD_API_TOKEN n'est pas définie dans le fichier .env")

OUTPUT_PATH = "/var/www/ctf-event/index.html"

# Fenêtre de temps du CTF (Du 12 octobre 2025 à 00:00:00 au 22 octobre 2025 à 23:59:59 UTC)
CTF_START = datetime(2025, 10, 12, 0, 0, 0, tzinfo=timezone.utc)
CTF_END   = datetime(2025, 10, 22, 23, 59, 59, tzinfo=timezone.utc)

# La liste stricte de tes challenges pour l'événement annuel
EVENT_CHALLENGE_IDS = [
    1, 2, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 
    21, 22, 24, 29, 30, 31, 32, 33, 35, 36, 37, 39, 40, 41, 42, 
    43, 44, 45, 46, 48, 49, 52, 53, 54, 55, 56, 57, 58, 59, 60, 
    61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 72, 85, 89, 92, 95, 
    97, 98, 99, 100, 101, 103, 104, 105, 106, 107, 109, 110, 111, 
    112, 113
]# ---------------------

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def build_scoreboard():
    scoreboard = {}
    
    print(f"[*] Récupération des résolutions pour les {len(EVENT_CHALLENGE_IDS)} challenges cibles...")

    for chall_id in EVENT_CHALLENGE_IDS:
        try:
            # Récupération de l'historique des validations pour ce challenge spécifique
            response = requests.get(f"{CTFD_URL}/challenges/{chall_id}/solves", headers=HEADERS, timeout=5)
            
            if response.status_code != 200:
                print(f"[!] Impossible de récupérer les données du challenge ID {chall_id} (Code {response.status_code})")
                continue
                
            solves_data = response.json().get('data', [])
            
            # Récupération de la valeur en points dynamique du challenge
            chall_info = requests.get(f"{CTFD_URL}/challenges/{chall_id}", headers=HEADERS, timeout=5)
            chall_value = chall_info.json().get('data', {}).get('value', 0) if chall_info.status_code == 200 else 0

            for solve in solves_data:
                username = solve.get('account_name') or solve.get('name') or solve.get('username')
                if not username:
                    continue
                    
                solve_date_str = solve.get('date')
                solve_time = datetime.min.replace(tzinfo=timezone.utc)
                
                if solve_date_str:
                    try:
                        # Nettoyage et conversion de la date CTFd au format ISO Python
                        clean_date = solve_date_str.replace('Z', '+00:00')
                        solve_time = datetime.fromisoformat(clean_date)
                    except Exception:
                        continue # Si la date est corrompue, on ignore le solve par sécurité

                # FILTRE TEMPOREL : On vérifie si la soumission s'inscrit dans les limites du CTF
                if CTF_START <= solve_time <= CTF_END:
                    # Initialisation du joueur s'il s'agit de son premier flag valide retenu
                    if username not in scoreboard:
                        scoreboard[username] = {"score": 0, "last_solve": solve_time}

                    # Accumulation des points du défi
                    scoreboard[username]["score"] += chall_value
                    
                    # Tie-break : mise à jour de l'horodatage si la soumission est plus récente
                    if solve_time > scoreboard[username]["last_solve"]:
                        scoreboard[username]["last_solve"] = solve_time
                else:
                    # Log d'information optionnel pour le débug en console
                    print(f"[!] Flag hors-délai ignoré pour {username} sur le challenge {chall_id} : {solve_time}")

        except Exception as e:
            print(f"[-] Erreur lors du traitement du challenge {chall_id} : {e}")

    # Tri final (Plus haut score d'abord, puis le joueur le plus rapide en cas d'égalité)
    sorted_ranking = sorted(scoreboard.items(), key=lambda x: (-x[1]['score'], x[1]['last_solve']))
    print(f"[*] Nombre de joueurs qualifiés dans la fenêtre temporelle : {len(sorted_ranking)}")

    # --- GÉNÉRATION HTML ---
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classement Live - CTF Événement</title>
    <meta http-equiv="refresh" content="30"> 
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans antialiased min-h-screen flex flex-col items-center py-12 px-4">
    <div class="w-full max-w-4xl">
        <header class="text-center mb-12">
            <h1 class="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-green-400 to-green-500 bg-clip-text text-transparent">
                Classement du 7TF 2025
            </h1>
            <p class="text-slate-400 mt-2 text-sm">Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Heure Serveur)</p>
        </header>

        <main class="bg-slate-800 rounded-xl shadow-2xl border border-slate-700 overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-700 text-slate-300 font-semibold text-sm tracking-wider uppercase border-b border-slate-600">
                        <th class="py-4 px-6 w-20 text-center">Rang</th>
                        <th class="py-4 px-6">Pseudo</th>
                        <th class="py-4 px-6 text-right w-36">Score</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-700">
    """

    for rank, (user, data) in enumerate(sorted_ranking, start=1):
        rank_display = str(rank)
        if rank == 1: rank_display = "🥇"
        elif rank == 2: rank_display = "🥈"
        elif rank == 3: rank_display = "🥉"

        html_content += f"""
                    <tr class="hover:bg-slate-750/50 transition-colors">
                        <td class="py-4 px-6 text-center font-bold text-lg">{rank_display}</td>
                        <td class="py-4 px-6 font-medium text-slate-200">{user}</td>
                        <td class="py-4 px-6 text-right font-mono font-bold text-green-400 text-lg">{data['score']} pts</td>
                    </tr>
        """
    
    if not sorted_ranking:
        html_content += """
                    <tr>
                        <td colspan="3" class="py-12 text-center text-slate-400">Aucun flag validé durant la période du CTF pour ces challenges.</td>
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

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Scoreboard filtré par date mis à jour avec succès à {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    build_scoreboard()
