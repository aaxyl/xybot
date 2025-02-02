import datetime

import discord, requests, asyncio, aiohttp, random, time
from time import sleep
from discord.ext import commands
from typing import Dict, List

# Initialize data structures
user_message_counts: Dict[str, int] = {}  # For rate limiting
chat_history: Dict[str, List[str]] = {}  # For context windows
user_configs: Dict[str, Dict[str, str | float]] = {}  # For user-specific configurations

intents = discord.Intents.default()  # Defining intents
intents.message_content = True  # Adding the message_content intent so that the bot can read user messages

# List of available models
models = [
    'hf.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:Q8_0',  # [0] DeepSeek R1 Distill Qwen 7B GGUF 8-bit
    'hf.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:Q4_K_M'  # [1] DeepSeek R1 Distill Qwen 7B GGUF 4-bit
]

# Used for testing/defaults
api_url = 'http://localhost:42069/api/generate'
default_model = models[1]
default_temp = 0.7

# Changing timeout settings for aiohttp
my_timeout = aiohttp.ClientTimeout(
    total=1350,  # total timeout (time consists connection establishment for a new connection or waiting for a free
    # connection from a pool if pool connection limits are exceeded) default value is 5 minutes, set to `None` or `0`
    # for unlimited timeout

    sock_connect=10,  # Maximal number of seconds for connecting to a peer for a new connection, not given from a
    # pool. See also connect.

    sock_read=900  # Maximal number of seconds for reading a portion of data from a peer
)

client_args = dict(
    trust_env=True,
    timeout=my_timeout
)


# Initializes the class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.ai_request_in_progress = False


bot = MyBot()


# Initialize the bot
@bot.event
async def on_ready():
    await change_bot_status("available")
    print("Bot is ready. Use this link to it to your guild: \n"
          "https://discord.com/oauth2/authorize?client_id="
          "1053809317314318378&permissions=18432&integration_type=0&scope=bot")


@bot.command()
async def config(ctx, model: str = None, temperature: float = None):
    """
    Configure the AI settings for your conversations.
    Usage:
    !config [model] [temperature]
    """
    user_id = str(ctx.author.id)
    # Store user-specific configurations
    user_configs[user_id] = {
        "model": model or "deepseek-r1-d-qwen-gguf:8b",
        "temperature": temperature or 0.7
    }
    await ctx.send(
        f"Configured: Model={user_configs[user_id]['model']}, Temperature={user_configs[user_id]['temperature']}")


async def random_wait_text(ctx, input_time):
    flavour_texts = \
        [
            f"***{ctx.author}** is stinky*",
            f"***{ctx.author}** thinks **{random.sample(ctx.guild.members, 1)[0].name}** is stinky*",
            f"***{ctx.author}** thinks **{random.sample(ctx.guild.members, 1)[0].name}** smells nice*",
            f"***{ctx.author}** likes to eat **{random.sample(ctx.guild.members, 1)[0].name}**'s toes*",
            f"***{bot.user}** is the best bot to ever exist 😎*",
            f"*1, 2, 3, 4... what comes after 4 again?*",
            f"*All your memes are belong to us*",
            f"***{ctx.author}** has a crush on **{random.sample(ctx.guild.members, 1)[0].name}***",
            f"***{random.sample(ctx.guild.members, 1)[0].name}** likes to smell **{ctx.author}**'s shirts*"
        ]

    now_time = time.time()
    embed_message = discord.Embed(
        title=f"{random.choice(flavour_texts)}",
        description=f"[{str(datetime.timedelta(seconds=round(now_time-input_time)))}] "
                    f"Brought to you by **Spicy Text Pty Ltd**"
    )
    await ctx.channel.send(embed=embed_message, delete_after=45.0)


async def send_reminder(ctx):
    start_time = time.time()
    sleep_time = 45
    while True:
        await asyncio.sleep(sleep_time)  # Sleep for 60 starts initially, then increases as time goes on
        await random_wait_text(ctx, start_time)
        if sleep_time > 180:
            sleep_time = 180
            await ctx.channel.send(
                "*Please wait, the response is still processing ()... :woozy_face: *",
                delete_after=30.0
            )
        sleep_time += 25


async def send_large_message(ctx, output_message):
    chunk_size = 2000
    index = 0
    while index < len(output_message):
        # Get the next chunk of text
        chunk = output_message[index:index + chunk_size]
        # Sends chunk out to channel
        await ctx.channel.send(chunk)
        # Move to the next chunk
        index += chunk_size
        sleep(2)


async def process_large_message(ctx, output_message):
    chunk_size = 4000
    whole_chunk = []
    index = 0
    while index < len(output_message):
        # Get the next chunk of text
        chunk = output_message[index:index + chunk_size]
        # Sends chunk out to channel
        whole_chunk.append(chunk)
        # Move to the next chunk
        index += chunk_size

    return whole_chunk


async def fetch_ollama_data(payload):
    async with aiohttp.ClientSession(**client_args) as session:
        async with session.post(api_url, json=payload) as response:
            return await response.json()


async def change_bot_status(status):
    if status == "available":
        available_statuses = [
            discord.CustomActivity(
                name="💣 Armed and primed 💣",
            ),
            discord.CustomActivity(
                name="💣 Lock n loaded 💣",
            ),
            discord.CustomActivity(
                name="💣 It's time to kick gum and chew ass 💣",
            )
        ]
        await bot.change_presence(
            status=discord.Status.online,
            activity=random.choice(available_statuses)
        )
    elif status == "busy":
        busy_statuses = [
            discord.CustomActivity(
                name="🐓 Streaming your data back to China 🐓",
            ),
            discord.CustomActivity(
                name="🐓 Choking the AI chicken 🐓",
            ),
            discord.CustomActivity(
                name="🐓 Sending data to your mom 🐓",
            )
        ]

        await bot.change_presence(
            status=discord.Status.dnd,
            activity=random.choice(busy_statuses)
        )


def round_seconds(obj: datetime.datetime) -> datetime.datetime:
    if obj.microsecond >= 500_000:
        obj += datetime.timedelta(seconds=1)
    return obj.replace(microsecond=0)


@bot.event
async def on_message(message):
    # print(message.content)
    if message.content.startswith('!ai'):

        current_model = ""
        current_temp = -1

        print(f"Processing prompt from user: {message.author}")
        # Check if the message is from a user and not the bot itself
        if message.author == bot.user:
            return

        if bot.ai_request_in_progress:
            await message.channel.send("Sorry, I'm already processing an AI request. Please wait.")
            return

        bot.ai_request_in_progress = True

        # Rate limiting (1 message per user every 60 seconds)
        user_id = str(message.author.id)
        current_count = user_message_counts.get(user_id, 0) + 1
        user_message_counts[user_id] = current_count

        if current_count > 5:
            await message.channel.send("You've exceeded the message limit. Please try again later.")
            return

        # Add the user's message to the chat history
        chat_history[user_id] = chat_history.get(user_id, [])
        chat_history[user_id].append(f"User: {message.content}")

        if len(chat_history[user_id]) > 5:
            chat_history[user_id] = chat_history[user_id][-5:]

        # Get user-specific configurations
        # config = user_configs.get(
        #     user_id, {"model": "hf.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:Q8_0", "temperature": 0.7}
        # )

        if current_model == "":
            current_model = default_model
        if current_temp == -1:
            current_temp = default_temp

        await change_bot_status("busy")

        start_time = round_seconds(datetime.datetime.now())

        print(f"Start time: {start_time} (0s)")

        await message.channel.send(f"Generating an answer for **{message.author}** at "
                                   f"**({start_time})** using **'{current_model}'**")

        loading_gif = discord.Embed(
            title="Processing your question..."
        )

        loading_gifs = [
            "https://c.tenor.com/zP2FVpaCZMkAAAAd/tenor.gif",
            "https://c.tenor.com/zAJgVsraM6UAAAAd/tenor.gif",
            "https://c.tenor.com/qU7kKSP7JgsAAAAC/tenor.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZWJzc2k4ODJsazM5bTd3dGNqdjk3OXJ5OGlqeG9o"
            "amlsZjhqZmUyayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ihVjxokZuNswo/giphy.gif",
            "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExOTd3NHByYjRkZDMybXZzaDU1bDF1Njk3anNsdWE5c"
            "HVpNWtieWNrNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l46Ck4CGc762ion28/giphy.gif",
            "https://c.tenor.com/KEzW7ALwfUAAAAAC/tenor.gif"
        ]

        loading_gif.set_image(url=random.choice(loading_gifs))

        lgmsg = await message.channel.send(embed=loading_gif)

        remind_task = asyncio.create_task(send_reminder(message))

        try:
            # response = requests.post(
            #     'http://localhost:42069/api/generate',
            #     json={
            #         "model": "hf.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:Q8_0",
            #         "prompt": message.content[len('!ai '):],
            #         "temperature": 0.7,
            #         "stream": False
            #     }
            # )

            # "model": config["model"],
            # "prompt": f"Chat history:\n{chat_history[user_id]}\n\nUser: {message.content[len('!ai '):]}",
            # "temperature": config["temperature"],
            # "stream": False

            payload = {
                "model": current_model,
                "prompt": message.content[len('!ai '):],
                "temperature": current_temp,
                "stream": False
            }

            response = await fetch_ollama_data(payload)

        except requests.exceptions.RequestException as e:
            await message.channel.send(f"Error: Could not connect to the AI server. Please try again later.")
            return

        except asyncio.exceptions.TimeoutError as e:
            finish_time = round_seconds(datetime.datetime.now())
            await message.channel.send(f"Error: Your prompt was too complex! AI timed out after 10 minutes. "
                                       f"({finish_time-start_time})")
            return

        finally:
            bot.ai_request_in_progress = False
            await change_bot_status("available")
            remind_task.cancel()

        # if response.status_code != 200:
        #     await message.channel.send("Error: Invalid request or response from the AI server.")
        #     bot.ai_request_in_progress = False
        #     await bot.change_presence(
        #         status=discord.Status.online
        #     )
        #     return

        try:
            print(f"Response: {response}")
            # data = response.json()
            data = response
            ai_response = data["response"]

        except KeyError as e:
            await message.channel.send("Error: Could not parse the AI response.")
            return

        finally:
            bot.ai_request_in_progress = False
            await change_bot_status("available")

        if ai_response.startswith("<think>\n\n</think>"):
            ai_response = ai_response.replace(
                "<think>\n\n</think>", "", 1
            ).replace(
                "Answer:", "# [Answer]", 1
            )
        else:
            ai_response = (
                ai_response.replace(
                    "<think>", "**[Megathonk mode]**", 1)
                .replace(
                    "</think>", "**[Megathonk stop]**", 1
                )
                .replace(
                    "Answer:", "**[Answer]**", 1
                )
            )

        await lgmsg.delete()

        # await send_large_message(message, ai_response)
        full_message = await process_large_message(message, ai_response)

        end_time = round_seconds(datetime.datetime.now())
        print(f"End time: {end_time} ({end_time-start_time})")

        await message.channel.send(
            f"# [{end_time-start_time}] "
            f"Dinner is served 😎")

        for index, msg in enumerate(full_message):
            fmsg = msg
            title_append = ""
            if index == 0:
                if len(full_message) > 1:
                    title_append = "\n**<Part 1>**\n"
                embed_message = discord.Embed(
                    title=f"**Answer for {message.author} by {bot.user}**",
                    description=f"Q: \"{message.content[len('!ai '):]}\"\nA: {title_append}{msg}"
                )
                await message.channel.send(embed=embed_message)
                continue
            elif index > 0:
                fmsg = f"-{msg}"
            embed_message = discord.Embed(title=f"**<Part {index + 1}>**", description=f"{fmsg}")
            await message.channel.send(embed=embed_message)


# When setting this for yourself, DO NOT GIVE IT TO ANYONE ELSE
bot.run("<Discord bot token goes here>")
