import os
import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer

print("🚀 Démarrage du bot...")

# Vérification du token
token = os.environ.get("token_bot_aternos")

if not token:
    print("❌ ERREUR: token_bot_aternos manquant!")
    exit(1)
else:
    print("✅ Token Discord trouvé")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

serveurs = {
    "ovni": "ovni_.aternos.me:52205",
    "survie": "surviefenix.aternos.me:22723",
    "cache-cache": "mapcachecache.aternos.me:62945"
}
messages_envoyés = {}
derniers_statuts = {}

SALON_ID = 1388916796211466250

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    print(f"🏠 Bot présent dans {len(bot.guilds)} serveur(s)")
    
    # Test du salon
    canal = bot.get_channel(SALON_ID)
    if canal:
        print(f"✅ Salon trouvé: {canal.name}")
        try:
            await canal.send("🤖 Bot de surveillance des serveurs Minecraft démarré!")
        except Exception as e:
            print(f"❌ Erreur envoi message test: {e}")
    else:
        print("❌ Salon introuvable!")
    
    print("🔍 Démarrage de la surveillance des serveurs...")
    try:
        verifier_serveurs.start()
        print("✅ Tâche de surveillance démarrée")
    except Exception as e:
        print("❌ Erreur tâche de vérif :", e)

@tasks.loop(seconds=15)
async def verifier_serveurs():
    canal = bot.get_channel(SALON_ID)
    if canal is None:
        print("❌ Salon introuvable dans la tâche.")
        return

    for nom, adresse in serveurs.items():
        try:
            serveur = JavaServer.lookup(adresse)
            statut = serveur.status()
            joueurs = statut.players.online
            message_texte = f"🟢 Le serveur **{nom}** est en ligne avec **{joueurs} joueur(s)**."

            statut_actuel = True
            
            if derniers_statuts.get(nom) != statut_actuel:
                print(f"✅ Serveur {nom} maintenant ONLINE ({joueurs} joueurs)")
                derniers_statuts[nom] = statut_actuel

            if nom in messages_envoyés and messages_envoyés[nom]:
                try:
                    await messages_envoyés[nom].edit(content=message_texte)
                except:
                    # Si le message n'existe plus, en créer un nouveau
                    msg = await canal.send(message_texte)
                    messages_envoyés[nom] = msg
            else:
                msg = await canal.send(message_texte)
                messages_envoyés[nom] = msg

        except Exception as e:
            statut_actuel = False
            
            if derniers_statuts.get(nom) != statut_actuel:
                print(f"🔴 Serveur {nom} maintenant OFFLINE: {e}")
                derniers_statuts[nom] = statut_actuel
            
            if nom in messages_envoyés and messages_envoyés[nom]:
                try:
                    await messages_envoyés[nom].delete()
                except:
                    pass
                messages_envoyés[nom] = None

# Commande simple pour tester le bot
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Bot fonctionnel!")

@bot.command()
async def serveurs_status(ctx):
    """Affiche le statut de tous les serveurs"""
    embed = discord.Embed(title="📊 Statut des serveurs Minecraft", color=0x00ff00)
    
    for nom, adresse in serveurs.items():
        try:
            serveur = JavaServer.lookup(adresse)
            statut = serveur.status()
            joueurs = statut.players.online
            embed.add_field(
                name=f"🟢 {nom}",
                value=f"**{joueurs}** joueur(s) connecté(s)",
                inline=True
            )
        except:
            embed.add_field(
                name=f"🔴 {nom}",
                value="Serveur hors ligne",
                inline=True
            )
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    print("🎯 Tentative de connexion...")
    try:
        bot.run(token)
    except Exception as e:
        print("❌ Erreur au lancement :", e)
        import traceback
        traceback.print_exc()
