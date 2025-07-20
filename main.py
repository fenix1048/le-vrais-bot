import os
import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import aiohttp
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = True
bot = commands.Bot(command_prefix="!", intents=intents)

serveurs = {
    "ovni": "ovni_.aternos.me:52205",
    "survie": "surviefenix.aternos.me:22723",
    "cache-cache": "mapcachecache.aternos.me:62945"
}
messages_envoyés = {}

SALON_ID = 1388916796211466250
OWNER_ID = 1352768109399900191
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
pending_questions = {}

async def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"❌ Erreur IA ({resp.status})"

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    try:
        verifier_serveurs.start()
    except Exception as e:
        print("❌ Erreur tâche de vérif :", e)

@tasks.loop(seconds=10)
async def verifier_serveurs():
    canal = bot.get_channel(SALON_ID)
    if canal is None:
        print("❌ Salon introuvable.")
        return

    serveurs_en_ligne = []
    
    # Vérifier quels serveurs sont en ligne
    for nom, adresse in serveurs.items():
        try:
            serveur = JavaServer.lookup(adresse)
            statut = serveur.status()
            joueurs = statut.players.online
            serveurs_en_ligne.append((nom, joueurs))
        except Exception as e:
            pass
    
    # Si aucun serveur en ligne, supprimer tous les messages
    if not serveurs_en_ligne:
        for nom in serveurs.keys():
            if nom in messages_envoyés and messages_envoyés[nom]:
                try:
                    await messages_envoyés[nom].delete()
                except:
                    pass
                messages_envoyés[nom] = None
        return
    
    # Gérer les serveurs en ligne
    for nom, joueurs in serveurs_en_ligne:
        message_texte = f"🟢 Le serveur **{nom}** est en ligne avec **{joueurs} joueur(s)**."
        
        if nom in messages_envoyés and messages_envoyés[nom]:
            try:
                await messages_envoyés[nom].edit(content=message_texte)
            except:
                # Si le message n'existe plus, on en crée un nouveau
                msg = await canal.send(message_texte)
                messages_envoyés[nom] = msg
        else:
            msg = await canal.send(message_texte)
            messages_envoyés[nom] = msg
    
    # Supprimer les messages des serveurs qui ne sont plus en ligne
    for nom in serveurs.keys():
        if nom not in [s[0] for s in serveurs_en_ligne]:
            if nom in messages_envoyés and messages_envoyés[nom]:
                try:
                    await messages_envoyés[nom].delete()
                except:
                    pass
                messages_envoyés[nom] = None

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel) and message.author.id == OWNER_ID:
        if message.author.id in pending_questions:
            data = pending_questions.pop(message.author.id)
            data['task'].cancel()

            if message.content.strip() == "1":
                response = await get_ai_response(data['prompt'])
                await data['message'].channel.send(response)
            elif message.content.startswith("!"):
                await data['message'].channel.send(message.content[1:].strip())

    elif message.content.lower().startswith("kairo "):
        prompt = message.content[6:].strip()
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            await owner.send(
                f"📩 Une question a été posée : `{prompt}`\n"
                f"Réponds avec `1` pour IA ou `!` pour une réponse personnalisée.\n"
                f"⏳ Tu as 10 secondes pour commencer à taper."
            )

            task = asyncio.create_task(auto_reply_ai(OWNER_ID, message, prompt))
            pending_questions[OWNER_ID] = {
                "message": message,
                "prompt": prompt,
                "task": task,
                "typing_started": None
            }
    else:
        await bot.process_commands(message)

@bot.event
async def on_typing(channel, user, when):
    if isinstance(channel, discord.DMChannel) and user.id == OWNER_ID:
        if OWNER_ID in pending_questions:
            pending_questions[OWNER_ID]['typing_started'] = datetime.utcnow()

async def auto_reply_ai(owner_id, original_msg, prompt):
    try:
        await asyncio.sleep(10)
        data = pending_questions.get(owner_id)
        if not data:
            return

        typing_time = data.get("typing_started")
        if typing_time and (datetime.utcnow() - typing_time).total_seconds() < 15:
            task = asyncio.create_task(auto_reply_ai(owner_id, original_msg, prompt))
            data["task"] = task
            data["typing_started"] = None
            return

        pending_questions.pop(owner_id)
        response = await get_ai_response(prompt)
        await original_msg.channel.send(response)

    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        bot.run(os.environ["token_bot_aternos"])
    except Exception as e:
        print("❌ Erreur au lancement :", e)
