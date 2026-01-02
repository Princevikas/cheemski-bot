import time, re
import function as func

from typing import List, Dict, Union, Optional

from discord import User, Member, VoiceChannel
from discord.ext import commands
from voicelink import Player, Track, Playlist, NodePool, decode, LoopType, Filters
from addons import LYRICS_PLATFORMS

RATELIMIT_COUNTER: Dict[int, Dict[str, float]] = {}
SCOPES = {
    "prefix": str,
    "lang": str,
    "queue_type": str,
    "dj": int,
    "controller": bool,
    "controller_msg": bool,
    "24/7": bool,
    "disabled_vote": bool,
    "duplicate_track": bool,
    "silent_msg": bool,
    "default_controller": dict,
    "stage_announce_template": str,
    "welcomer": dict,
    "goodbye": dict,
    "leveling": dict
}

class SystemMethod:
    def __init__(self, function: callable, *, credit: int = 1):
        self.function: callable = function
        self.params: List[str] = ["bot", "data"]
        self.credit: int = credit

class PlayerMethod(SystemMethod):
    def __init__(self, function, *, credit: int = 1, auto_connect: bool = False):
        super().__init__(function, credit=credit)
        self.params: List[str] = ["player", "member", "data"]
        self.auto_connect: bool = auto_connect

def require_permission(only_admin: bool = False):
    def decorator(func) -> callable:
        async def wrapper(player: Player, member: Member, dict: Dict) -> Optional[Dict]:
            if only_admin and not member.guild_permissions.manage_guild:
                return error_msg("Only the admins may use this function!", user_id=member.id)
            if not player.is_privileged(member):
                return error_msg("Only the DJ or admins may use this function!", user_id=member.id)
            return await func(player, member, dict)
        return wrapper
    return decorator

def error_msg(msg: str, *, user_id: int = None, guild_id: int = None, level: str = "info") -> Dict:
    payload = {"op": "errorMsg", "level": level, "msg": msg}
    if user_id:
        payload["userId"] = str(user_id)
    if guild_id:
        payload["guildId"] = str(guild_id)

    return payload

async def connect_channel(member: Member, bot: commands.Bot) -> Player:
    if not member.voice:
        return

    channel = member.voice.channel
    try:
        settings = await func.get_settings(channel.guild.id)
        player: Player = await channel.connect(cls=Player(bot, channel, func.TempCtx(member, channel), settings))
        await player.send_ws({"op": "createPlayer", "memberIds": [str(member.id) for member in channel.members]})
        return player
    except:
        return

async def initBot(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))
    user = bot.get_user(user_id)
    if not user:
        user = await bot.fetch_user(user_id)

    if user:
        # Check if user is admin (bot owner or in bot_access_user list)
        bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
        is_owner = await bot.is_owner(user)
        is_admin = is_owner or user_id in bot_access_users
        
        # Calculate bot stats
        server_count = len(bot.guilds)
        user_count = sum(g.member_count or 0 for g in bot.guilds)
        command_count = len([c for c in bot.tree.walk_commands()])
        
        # Count active music players
        active_players = sum(1 for g in bot.guilds if g.voice_client and g.voice_client.is_playing)
        
        # Calculate uptime
        import time
        uptime_seconds = int(time.time() - getattr(bot, 'start_time', time.time()))
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        if uptime_hours >= 24:
            uptime_str = f"{uptime_hours // 24}d {uptime_hours % 24}h"
        elif uptime_hours > 0:
            uptime_str = f"{uptime_hours}h {uptime_minutes}m"
        else:
            uptime_str = f"{uptime_minutes}m"
        
        return {
            "op": "initBot",
            "userId": str(user_id),
            "botName": bot.user.display_name,
            "botAvatar": bot.user.display_avatar.url,
            "botId": str(bot.user.id),
            "isAdmin": is_admin,
            # Bot stats
            "serverCount": server_count,
            "userCount": user_count,
            "commandCount": command_count,
            "activePlayers": active_players,
            "uptime": uptime_str
        }
    
async def initUser(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))
    user_data = await func.get_user(user_id)
    
    # Check if user is admin (for shared inbox)
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    is_owner = await bot.is_owner(bot.get_user(user_id) or await bot.fetch_user(user_id))
    is_admin = is_owner or user_id in bot_access_users
    
    # For admins, load SHARED inbox from all bot_access_users
    if is_admin:
        all_inbox = []
        seen_ids = set()  # Avoid duplicates
        
        for admin_id in bot_access_users:
            try:
                admin_data = await func.get_user(admin_id)
                for mail in admin_data.get("inbox", []):
                    # Create unique ID for deduplication
                    mail_id = f"{mail.get('time', '')}-{mail.get('title', '')}-{mail.get('type', '')}"
                    if mail_id not in seen_ids:
                        seen_ids.add(mail_id)
                        all_inbox.append(mail)
            except Exception as e:
                func.logger.debug(f"Could not load inbox for admin {admin_id}: {e}")
        
        # Also include owner's inbox if different
        if is_owner and user_id not in bot_access_users:
            for mail in user_data.get("inbox", []):
                mail_id = f"{mail.get('time', '')}-{mail.get('title', '')}-{mail.get('type', '')}"
                if mail_id not in seen_ids:
                    seen_ids.add(mail_id)
                    all_inbox.append(mail)
        
        # Sort by time (newest first)
        all_inbox.sort(key=lambda x: x.get("time", "0"), reverse=True)
        user_data["inbox"] = all_inbox
    
    # Process inbox messages (add sender info)
    for mail in user_data.get("inbox", [])[:]:  # Use slice copy to safely modify
        sender_id = mail.get("sender")
        mail_type = mail.get("type", "")
        
        # Handle suggestions (may have None sender for anonymous)
        if mail_type == "suggestion":
            sender_name = mail.get("sender_name") or "Anonymous"
            mail["sender"] = {
                "avatarUrl": None, 
                "name": sender_name, 
                "id": str(sender_id) if sender_id else None
            }
            continue
        
        # Handle anonymous messages (sender is None)
        if sender_id is None:
            mail["sender"] = {
                "avatarUrl": None, 
                "name": mail.get("sender_name") or "Anonymous", 
                "id": None
            }
            continue
        
        # Handle normal inbox messages with sender ID
        try:
            sender = bot.get_user(sender_id)
            if not sender:
                sender = await bot.fetch_user(sender_id)
            
            if sender:
                mail["sender"] = {"avatarUrl": sender.display_avatar.url, "name": sender.display_name, "id": str(sender.id)}
            else:
                # Sender not found, remove this mail
                user_data.get("inbox").remove(mail)
        except:
            # Invalid sender ID, remove this mail
            user_data.get("inbox").remove(mail)

    return {
        "op": "initUser",
        "userId": str(user_id),
        "data": user_data
    }
    
async def initPlayer(player: Player, member: Member, data: Dict) -> Dict:
    player._ipc_connection = True
    available_filters = []
    for name, filter_cls in Filters.get_available_filters().items():
        filter = filter_cls()
        available_filters.append({"tag": name, "scope": filter.scope, "payload": filter.payload})

    return {
        "op": "initPlayer",
        "guildId": str(player.guild.id),
        "userId": str(data.get("userId")),
        "users": [{
            "userId": str(member.id),
            "avatarUrl": member.display_avatar.url,
            "name": member.name
        } for member in player.channel.members ],
        "tracks": [ {"trackId": track.track_id, "requesterId": str(track.requester.id)} for track in player.queue._queue ],
        "repeatMode": player.queue.repeat.lower(),
        "channelName": player.channel.name,
        "currentQueuePosition": player.queue._position + (0 if player.is_playing else 1),
        "currentPosition": 0 or player.position if player.is_playing else 0,
        "isPlaying": player.is_playing,
        "isPaused": player.is_paused,
        "isDj": player.is_privileged(member, check_user_join=False),
        "autoplay": player.settings.get("autoplay", False),
        "volume": player.volume,
        "filters": [{"tag": filter.tag, "scope": filter.scope, "payload": filter.payload} for filter in player.filters.get_filters()],
        "availableFilters": available_filters
    }

async def closeConnection(bot: commands.Bot, data: Dict) -> None:
    guild_id = int(data.get("guildId"))
    guild = bot.get_guild(guild_id)
    player: Player = guild.voice_client
    if player:
        player._ipc_connection = False

async def getRecommendation(bot: commands.Bot, data: Dict) -> None: 
    node = NodePool.get_node()
    if not node:
        return
    
    track_data = decode(track_id := data.get("trackId"))
    track = Track(track_id=track_id, info=track_data, requester=bot.user)
    tracks: List[Track] = await node.get_recommendations(track, limit=60)

    return {
        "op": "getRecommendation",
        "userId": str(data.get("userId")),
        "callback": data.get("callback"),
        "tracks": [track.track_id for track in tracks] if tracks else []
    }

async def skipTo(player: Player, member: Member, data: Dict) -> None:
    if not player.is_privileged(member):
        if player.current and member == player.current.requester:
            pass

        elif member in player.skip_votes:
            return error_msg(player.get_msg('voted'), user_id=member.id)
        
        else:
            player.skip_votes.add(member)
            if len(player.skip_votes) < (required := player.required()):
                return error_msg(player.get_msg('skipVote').format(member, len(player.skip_votes), required), guild_id=player.guild.id)

    index = data.get("index", 1)
    if index > 1:
        player.queue.skipto(index)

    if player.queue._repeat.mode == LoopType.TRACK:
        await player.set_repeat(LoopType.OFF)
    await player.stop()

async def backTo(player: Player, member: Member, data: Dict) -> None:
    if not player.is_privileged(member):
        if player.current and member == player.current.requester:
            pass

        elif member in player.skip_votes:
            return error_msg(player.get_msg('voted'), user_id=member.id)
        
        else:
            player.skip_votes.add(member)
            if len(player.skip_votes) < (required := player.required()):
                return error_msg(player.get_msg('backVote').format(member, len(player.skip_votes), required), guild_id=player.guild.id)
    
    index = data.get("index", 1)
    if not player.is_playing:
        player.queue.backto(index)
        await player.do_next()
    else:
        player.queue.backto(index + 1)
        await player.stop()

@require_permission()
async def moveTrack(player: Player, member: Member, data: Dict) -> None:
    index = data.get("index")
    new_index = data.get("newIndex")
    if index == new_index:
        return
    
    await player.move_track(index, new_index, member)

async def addTracks(player: Player, member: Member, data: Dict) -> None:
    _type = data.get("type", "addToQueue")
    tracks = [Track(
        track_id=track_id, 
        info=decode(track_id),
        requester=member
    ) for track_id in data.get("tracks", [])]

    if _type == "addToQueue":
        await player.add_track(tracks)

    elif _type == "forcePlay":
        await player.add_track(tracks, at_front=True)
        if player.is_playing:
            return await player.stop()
    
    elif _type == "addNext":
        await player.add_track(tracks, at_front=True)

    if not player.is_playing:
        await player.do_next()

async def getTracks(bot: commands.Bot, data: Dict) -> Dict:
    query = data.get("query", None)

    if query:
        payload = {"op": "getTracks", "userId": data.get("userId"), "callback": data.get("callback")}
        tracks = await NodePool.get_node().get_tracks(query=query, requester=None)
        if not tracks:
            return payload

        payload["tracks"] = [ track.track_id for track in (tracks.tracks if isinstance(tracks, Playlist) else tracks ) ]
        return payload

async def searchAndPlay(player: Player, member: Member, data: Dict) -> None:
    payload = await getTracks(player.bot, data)
    await addTracks(player, member, payload)

async def shuffleTrack(player: Player, member: Member, data: Dict) -> None:
    if not player.is_privileged(member):
        if member in player.shuffle_votes:
            return error_msg(player.get_msg('voted'), user_id=member.id) 

        player.shuffle_votes.add(member)
        if len(player.shuffle_votes) < (required := player.required()):
            return error_msg(player.get_msg('shuffleVote').format(member, len(player.skip_votes), required), guild_id=player.guild.id)
    
    await player.shuffle(data.get("type", "queue"), member)

@require_permission()
async def repeatTrack(player: Player, member: Member, data: Dict) -> None:
    await player.set_repeat(requester=member)

@require_permission()
async def removeTrack(player: Player, member: Member, data: Dict) -> None:
    index, index2 = data.get("index"), data.get("index2")
    await player.remove_track(index, index2, requester=member)

@require_permission()
async def clearQueue(player: Player, member: Member, data: Dict) -> None:
    queue_type = data.get("queueType", "").lower()
    await player.clear_queue(queue_type, member)

@require_permission(only_admin=True)
async def updateVolume(player: Player, member: Member, data: Dict) -> None:
    volume = data.get("volume", 100)
    await func.update_settings(player.guild.id, {"$set": {"volume": volume}})
    await player.set_volume(volume=volume, requester=member)

async def updatePause(player: Player, member: Member, data: Dict) -> None:
    pause = data.get("pause", True)
    if not player.is_privileged(member):
        if pause:
            if member in player.pause_votes:
                return error_msg(player.get_msg('voted'), user_id=member.id)

            player.pause_votes.add(member)
            if len(player.pause_votes) < (required := player.required()):
                return error_msg(player.get_msg('pauseVote').format(member, len(player.pause_votes), required), guild_id=player.guild.id)

        else:
            if member in player.resume_votes:
                return error_msg(player.get_msg('voted'), user_id=member.id)
            
            player.resume_votes.add(member)
            if len(player.resume_votes) < (required := player.required()):
                return error_msg(player.get_msg('resumeVote').format(member, len(player.resume_votes), required), guild_id=player.guild.id)

    await player.set_pause(pause, member)

@require_permission()
async def updatePosition(player: Player, member: Member, data: Dict) -> None:
    position = data.get("position");
    await player.seek(position, member);

async def toggleAutoplay(player: Player, member: Member, data: Dict) -> Dict:
    if not player.is_privileged(member):
        return error_msg(player.get_msg('missingAutoPlayPerm'))

    check = data.get("status", False)
    player.settings['autoplay'] = check

    if not player.is_playing:
        await player.do_next()

    return {
        "op": "toggleAutoplay",
        "status": check,
        "guildId": str(player.guild.id),
        "requesterId": str(member.id)
    }

@require_permission()
async def updateFilter(player: Player, member: Member, data: Dict) -> None:
    updateType = data.get("type", "add")
    filter_tag = data.get("tag")

    if updateType == "add":
        available_filters = Filters.get_available_filters()
        filter_cls = available_filters.get(filter_tag)
        if not filter_cls:
            return
        
        payload = {}
        if "payload" in data:
            payload = data.get("payload").get(list(data.get("payload").keys()[0]), {})
        if player.filters.has_filter(filter_tag=filter_tag):
            player.filters.remove_filter(filter_tag=filter_tag)
        await player.add_filter(filter=filter_cls(**payload), requester=member)

    elif updateType == "remove":
        await player.remove_filter(filter_tag=filter_tag, requester=member)

    else:
        await player.reset_filter(requester=member)

async def _loadPlaylist(playlist: Dict) -> Optional[List[Track]]:
    if playlist.get("type") == "link":
        tracks: List[Track]= await NodePool.get_node().get_tracks(playlist.get("uri"), requester=None)
        if tracks:
            return [track.track_id for track in (tracks.tracks if isinstance(tracks, Playlist) else tracks)]
    else:
        return playlist.get("tracks", [])

def _assign_playlist_id(existed: list) -> str:
    for i in range(200, 210):
        if str(i) not in existed:
            return str(i)
        
async def _getPlaylist(user_id: int, playlist_id: str) -> Dict:
    playlists = await func.get_user(user_id, "playlist")
    playlist = playlists.get(playlist_id)
    if not playlist:
        return
    
    if playlist["type"] == "share":
        target_user = await func.get_user(playlist["user"], "playlist")
        target_playlist = target_user.get(playlist["referId"])
        if target_playlist and user_id in target_playlist.get("perms", {}).get("read", []):
            playlist["tracks"] = await _loadPlaylist(target_playlist)
    else:
        playlist["tracks"] = await _loadPlaylist(playlist)

    return playlist

async def getPlaylist(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))
    playlist_id = str(data.get("playlistId"))

    payload = {"op": "loadPlaylist", "playlistId": playlist_id, "userId": str(user_id)}
    playlist = await _getPlaylist(user_id, playlist_id)
    payload["tracks"] = playlist["tracks"] if playlist else []
    
    return payload
    
async def updatePlaylist(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))
    playlist_id = str(data.get("playlistId"))
    _type = data.get("type")
    
    if not playlist_id and not _type == "createPlaylist":
        return error_msg("Unable to process this request without a playlist ID.", user_id=user_id, level="error")
    
    rank, max_p, max_t = func.check_roles()
    if _type == "createPlaylist":
        name, playlist_url = data.get("playlistName"), data.get("playlistUrl")
        if not name:
            return {
                "op": "updatePlaylist",
                "status": "error",
                "msg": f"You must enter name for this field!",
                "field": "playlistName",
                "userId": str(user_id)
            }
        
        playlist = await func.get_user(user_id, "playlist")
        if len(list(playlist.keys())) >= max_p:
            return {
                "op": "updatePlaylist",
                "status": "error",
                "msg": f"You cannot create more than '{max_p}' playlists!",
                "field": "playlistName",
                "userId": str(user_id)
            }

        for playlist_data in playlist.values():
            if playlist_data['name'].lower() == name.lower():
                return {
                    "op": "updatePlaylist",
                    "status": "error",
                    "msg": f"Playlist '{name}' already exists.",
                    "field": "playlistName",
                    "userId": str(user_id)
                }
        
        if playlist_url:
            tracks = await NodePool.get_node().get_tracks(playlist_url, requester=None)
            if not isinstance(tracks, Playlist):
                return {
                    "op": "updatePlaylist",
                    "status": "error",
                    "msg": f"Please enter a valid link or public spotify or youtube playlist link.",
                    "field": "playlistUrl",
                    "userId": str(user_id)
                }

        assigned_playlist_id = _assign_playlist_id(list(playlist.keys()))
        data = {'uri': playlist_url, 'perms': {'read': []}, 'name': name, 'type': 'link'} if playlist_url else {'tracks': [], 'perms': {'read': [], 'write': [], 'remove': []}, 'name': name, 'type': 'playlist'}
        await func.update_user(user_id, {"$set": {f"playlist.{assigned_playlist_id}": data}})
        return {
            "op": "updatePlaylist",
            "status": "created",
            "playlistId": assigned_playlist_id,
            "msg": f"You have created '{name}' playlist.",
            "userId": str(user_id),
            "data": data
        }
        
    elif _type == "removePlaylist":
        playlist = await _getPlaylist(user_id, playlist_id)
        if playlist:
            if playlist['type'] == 'share':
                await func.update_user(playlist['user'], {"$pull": {f"playlist.{playlist['referId']}.perms.read": user_id}})

            await func.update_user(user_id, {"$unset": {f"playlist.{playlist_id}": 1}})

        return {
            "op": "updatePlaylist",
            "status": "deleted",
            "playlistId": playlist_id,
            "msg": f"You have removed playlist '{playlist['name']}'",
            "userId": str(user_id)
        }
    
    elif _type == "renamePlaylist":
        name = data.get("name")
        if not name:
            return {
                "op": "updatePlaylist",
                "status": "error",
                "msg": f"You must enter name for this field!",
                "field": "playlistName",
                "userId": str(user_id)
            }
        
        playlist = await func.get_user(user_id, "playlist")
        for data in playlist.values():
            if data['name'].lower() == name.lower():
                return {
                    "op": "updatePlaylist",
                    "status": "error",
                    "msg": f"Playlist '{data['name']}' already exists.",
                    "field": "playlistName",
                    "userId": str(user_id)
                }

        await func.update_user(user_id, {"$set": {f'playlist.{playlist_id}.name': name}})
        return {
            "op": "updatePlaylist",
            "status": "renamed",
            "name": name,
            "playlistId": playlist_id,
            "msg": f"You have renamed the playlist to '{name}'.",
            "field": "playlistName",
            "userId": str(user_id)
        }
    
    elif _type == "addTrack":
        track_id = data.get("trackId")
        if not track_id:
            return error_msg("No track ID could be located.", user_id=user_id, level='error')
        
        playlist = await _getPlaylist(user_id, playlist_id)
        if playlist['type'] in ['share', 'link']:
            return error_msg("You cannot add songs to a linked playlist through Vocard.", user_id=user_id, level='error')
        
        rank, max_p, max_t = func.check_roles()
        if len(playlist['tracks']) >= max_t:
            return error_msg(f"You have reached the limit! You can only add {max_t} songs to your playlist.", user_id=user_id)

        decoded_track = Track(track_id=track_id, info=decode(track_id), requester=None)
        if decoded_track.is_stream:
            return error_msg("You are not allowed to add streaming videos to your playlist.", user_id=user_id)
        
        await func.update_user(user_id, {"$push": {f'playlist.{playlist_id}.tracks': track_id}})
        return {
            "op": "updatePlaylist",
            "status": "addTrack",
            "playlistId": playlist_id,
            "trackId": track_id,
            "msg": f"Added {decoded_track.title} into '{playlist['name']}' playlist.",
            "userId": str(user_id)
        }
        
    elif _type == "removeTrack":
        track_id, track_position = data.get("trackId"), data.get("trackPosition", 0)
        if not track_id:
            return error_msg("No track ID could be located.", user_id=user_id, level='error')
        
        playlist = await _getPlaylist(user_id, playlist_id)
        if not playlist:
            return error_msg("Playlist not found!", user_id=user_id, level='error')
        
        if playlist['type'] in ['share', 'link']:
            return error_msg("You cannot remove songs from a linked playlist through Vocard.", user_id=user_id, level='error')
        
        if not 0 <= track_position < len(playlist['tracks']):
            return error_msg("Cannot find the position from your playlist.", user_id=user_id, level="error")

        if playlist['tracks'][track_position] != track_id:
            return error_msg("Something wrong while removing the track from your playlist.", user_id=user_id, level='error')
        
        await func.update_user(user_id, {"$pull": {f'playlist.{playlist_id}.tracks': playlist['tracks'][track_position]}})
        
        decoded_track = decode(playlist['tracks'][track_position])
        return {
            "op": "updatePlaylist",
            "status": "removeTrack",
            "playlistId": playlist_id,
            "trackPosition": track_position,
            "trackId": track_id,
            "msg": f"Removed '{decoded_track['title']}' from '{playlist['name']}' playlist.",
            "userId": str(user_id)
        }

    elif _type == "updateInbox":
        user = await func.get_user(user_id)
        is_accept = data.get("accept", False)

        if is_accept and len(list(user.get("playlist").keys())) >= max_p:
            return error_msg(f"You cannot create more than '{max_p}' playlists!", user_id=user_id, level = "error")

        info = data.get("referId", "").split("-")
        sender_id, refer_id = info[0], info[1]
        inbox = user.get("inbox")

        payload = {"op": "updatePlaylist", "status": "updateInbox", "userId": str(user_id), "accept": is_accept, "senderId": sender_id, "referId": refer_id}
        for index, mail in enumerate(inbox.copy()):
            if not (str(mail.get("sender")) == sender_id and mail.get("referId") == refer_id):
                continue
            
            del inbox[index]
            if is_accept:
                share_playlists = await func.get_user(mail["sender"], "playlist")
                if refer_id not in share_playlists:
                    return error_msg("The shared playlist couldn’t be found. It’s possible that the user has already deleted it.", user_id=user_id)
                
                assigned_playlist_id = _assign_playlist_id(list(user.get("playlist", []).keys()))
                playlist_name = f"Share{time.strftime('%M%S', time.gmtime(int(mail['time'])))}"
                share_playlist = share_playlists.get(refer_id)
                share_playlist.update({
                    "name": playlist_name,
                    "type": "share"
                })
                await func.update_user(mail['sender'], {"$push": {f"playlist.{mail['referId']}.perms.read": user_id}})
                await func.update_user(user_id, {"$set": {
                    f'playlist.{assigned_playlist_id}': {
                        'user': mail['sender'], 'referId': mail['referId'],
                        'name': playlist_name,
                        'type': 'share'
                    },
                    "inbox": inbox
                }})

                payload.update({
                    "playlistId": assigned_playlist_id,
                    "msg": f"You have created '{playlist_name}' playlist.",
                    "data": share_playlist,
                })

            await func.update_user(user_id, {"$set": {"inbox": inbox}})
            return payload

async def getMutualGuilds(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))

    payload = {"op": "getMutualGuilds", "mutualGuilds": {}, "inviteGuilds": {}, "userId": str(user_id)}
    for guild_id, guild_info in data.get("guilds", {}).items():
        if guild := bot.get_guild(int(guild_id)):
            payload["mutualGuilds"][guild_id] = {
                **guild_info,
                "memberCount": guild.member_count
            }
        else:
            payload["inviteGuilds"][guild_id] = {**guild_info}

    return payload

async def getSettings(bot: commands.Bot, data: Dict) -> Dict:
    user_id = int(data.get("userId"))
    guild_id  = int(data.get("guildId"))

    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Vocard don't have access to requested guild.", user_id=user_id, level="error")

    member = guild.get_member(user_id)
    if not member:
        # Try fetching from API if not in cache
        try:
            member = await guild.fetch_member(user_id)
        except:
            pass
    if not member:
        return error_msg("You are not in the requested guild.", user_id=user_id, level="error")
    
    # Allow access if user has any of these permissions:
    # - Server Owner, Administrator, Manage Guild, Manage Channels, or Manage Messages
    has_permission = (
        member.id == guild.owner_id or  # Server owner
        member.guild_permissions.administrator or
        member.guild_permissions.manage_guild or
        member.guild_permissions.manage_channels or
        member.guild_permissions.manage_messages
    )
    if not has_permission:
        return error_msg("You don't have permission to access the settings.", user_id=user_id, level='error')
    
    settings = await func.get_settings(guild_id)
    if "dj" in settings:
        role = guild.get_role(settings["dj"])
        if role:
            settings["dj"] = role.name

    return {
        "op": "getSettings",
        "settings": settings,
        "options": {
            "languages": list(func.LANGS.keys()),
            "queueModes": ["Queue", "FairQueue"],
            "roles": [role.name for role in guild.roles],
            "textChannels": [{"id": str(ch.id), "name": ch.name} for ch in guild.text_channels]
        },
        "guild": {
            "avatar": guild.icon.url if guild.icon else None,
            "name": guild.name,
            "id": str(guild_id)
        },
        "userId": str(user_id)
    }

async def getLyrics(bot: commands.Bot, data: Dict) -> Dict:
    title, artist, platform = data.get("title", ""), data.get("artist", ""), data.get("platform", "")
    full_lyrics = data.get("full", False)  # Dashboard requests full lyrics
    
    if not platform or platform not in LYRICS_PLATFORMS:
        platform = func.settings.lyrics_platform
    
    # Try multiple platforms with fallback
    fallback_order = ["lrclib", "genius", "lyrist", "musixmatch", "a_zlyrics"]
    lyrics = None
    used_platform = platform
    
    # Try primary platform first
    lyrics_platform = LYRICS_PLATFORMS.get(platform)
    if lyrics_platform:
        try:
            lyrics = await lyrics_platform().get_lyrics(title, artist)
        except:
            pass
    
    # Fallback to other platforms if needed
    if not lyrics:
        for p in fallback_order:
            if p == platform:
                continue
            try:
                lyrics_platform = LYRICS_PLATFORMS.get(p)
                if lyrics_platform:
                    lyrics = await lyrics_platform().get_lyrics(title, artist)
                    if lyrics:
                        used_platform = p
                        break
            except:
                continue
    
    if lyrics:
        # Return full lyrics for dashboard, chunked for Discord
        if full_lyrics:
            lyrics_data = lyrics  # Full lyrics for dashboard
        else:
            lyrics_data = {_: re.findall(r'.*\n(?:.*\n){,22}', v or "") for _, v in lyrics.items()}
        
        return {
            "op": "getLyrics",
            "userId": data.get("userId"),
            "title": title,
            "artist": artist,
            "platform": used_platform,
            "lyrics": lyrics_data,
            "callback": data.get("callback")
        }
    
    return {
        "op": "getLyrics",
        "userId": data.get("userId"),
        "title": title,
        "artist": artist,
        "platform": platform,
        "lyrics": {},
        "callback": data.get("callback")
    }

async def updateSettings(bot: commands.Bot, data: Dict) -> None:
    user_id = int(data.get("userId"))
    guild_id  = int(data.get("guildId"))

    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Vocard don't have access to required guild.", user_id=user_id, level="error")

    member = guild.get_member(user_id)
    if not member:
        # Try fetching from API if not in cache
        try:
            member = await guild.fetch_member(user_id)
        except:
            pass
    if not member:
        return error_msg("You are not in the required guild.", user_id=user_id, level="error")
    
    # Allow access if user has any of these permissions:
    # - Server Owner, Administrator, Manage Guild, Manage Channels, or Manage Messages
    has_permission = (
        member.id == guild.owner_id or  # Server owner
        member.guild_permissions.administrator or
        member.guild_permissions.manage_guild or
        member.guild_permissions.manage_channels or
        member.guild_permissions.manage_messages
    )
    if not has_permission:
        return error_msg("You don't have permission to change the settings.", user_id=user_id, level='error')
    
    data = data.get("settings", {})
    if "dj" in data:
        for role in guild.roles:
            if role.name.lower() == data["dj"]:
                data["dj"] = role.id
                break

    for key, value in data.copy().items():
        if key not in SCOPES or not isinstance(value, SCOPES[key]):
            del data[key]

    await func.update_settings(guild.id, {"$set": data})

# ========== DASHBOARD EXTENDED METHODS ==========

async def getGuildChannels(bot: commands.Bot, data: Dict) -> Dict:
    """Get all text channels in a guild for channel selectors"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    callback = data.get("callback", "announce-channel-select")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    # Member check is optional - mutualGuilds already verified membership
    # If member cache miss, we still allow fetching channels
    
    channels = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            channels.append({
                "id": str(channel.id),
                "name": channel.name,
                "category": channel.category.name if channel.category else None
            })
    
    return {
        "op": "getGuildChannels",
        "channels": channels,
        "guildId": str(guild_id),
        "userId": str(user_id),
        "callback": callback
    }

async def sendAnnounce(bot: commands.Bot, data: Dict) -> Dict:
    """Send an announcement to a channel from dashboard"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    channel_id = int(data.get("channelId"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    # Try cache first, then fetch if not found
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return error_msg("Could not verify your membership in this guild.", user_id=user_id, level="error")
    
    # Check permission - configurable announce roles or default to manage_messages
    settings = await func.get_settings(guild_id)
    announce_roles = settings.get("announce_roles", [])
    
    has_permission = False
    
    # Check if user is admin/bot owner
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    is_owner = await bot.is_owner(member)
    
    if is_owner or user_id in bot_access_users:
        has_permission = True
    # Check if user has manage_messages (always allowed as moderator)
    elif member.guild_permissions.manage_messages:
        has_permission = True
    # Check if user has any of the configured announce roles
    elif announce_roles:
        member_role_ids = [role.id for role in member.roles]
        if any(role_id in member_role_ids for role_id in announce_roles):
            has_permission = True
    
    if not has_permission:
        return error_msg("You don't have permission to send announcements.", user_id=user_id, level="error")
    
    channel = guild.get_channel(channel_id)
    if not channel:
        return error_msg("Channel not found.", user_id=user_id, level="error")
    
    # Parse color
    import discord
    try:
        color_str = data.get("color", "#3498db").strip()
        if color_str.startswith("#"):
            color_str = color_str[1:]
        color = int(color_str, 16)
    except:
        color = 0x3498db
    
    # Create embed
    embed = discord.Embed(
        title=f"📢 {data.get('title', 'Announcement')}",
        description=data.get("description", ""),
        color=color
    )
    
    # Optional image
    if data.get("imageUrl"):
        embed.set_image(url=data.get("imageUrl"))
    
    # Anonymous or show user
    if data.get("anonymous"):
        embed.set_footer(text="Anonymous Announcement")
    else:
        embed.set_footer(
            text=f"Announced by {member.display_name}",
            icon_url=member.display_avatar.url
        )
    
    embed.timestamp = discord.utils.utcnow()
    
    try:
        await channel.send(embed=embed)
        return {
            "op": "sendAnnounce",
            "status": "success",
            "msg": f"Announcement sent to #{channel.name}!",
            "userId": str(user_id),
            "guildId": str(guild_id)
        }
    except Exception as e:
        return error_msg(f"Failed to send: {str(e)}", user_id=user_id, level="error")

async def getAuditSettings(bot: commands.Bot, data: Dict) -> Dict:
    """Get audit logging settings for a guild"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return error_msg("Could not verify your membership.", user_id=user_id, level="error")
    
    # Check permission
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    if not member.guild_permissions.administrator and user_id not in bot_access_users:
        return error_msg("You don't have permission to view audit settings.", user_id=user_id, level="error")
    
    settings = await func.get_settings(guild_id)
    audit_config = settings.get("audit", {})
    
    # Get auditor info
    auditors = []
    for auditor_id in audit_config.get("auditors", []):
        m = guild.get_member(auditor_id)
        if m:
            auditors.append({"id": str(auditor_id), "name": m.display_name, "avatar": str(m.display_avatar.url)})
    
    return {
        "op": "getAuditSettings",
        "enabled": audit_config.get("enabled", False),
        "channelId": str(audit_config.get("channel_id", "")) if audit_config.get("channel_id") else None,
        "auditors": auditors,
        "guildId": str(guild_id),
        "userId": str(user_id)
    }

async def updateAuditSettings(bot: commands.Bot, data: Dict) -> Dict:
    """Update audit logging settings"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return error_msg("Could not verify your membership.", user_id=user_id, level="error")
    
    # Check permission
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    if not member.guild_permissions.administrator and user_id not in bot_access_users:
        return error_msg("You don't have permission to change audit settings.", user_id=user_id, level="error")
    
    update_type = data.get("type")
    
    if update_type == "toggle":
        enabled = data.get("enabled", False)
        channel_id = int(data.get("channelId")) if data.get("channelId") else None
        await func.update_settings(guild_id, {"$set": {"audit.enabled": enabled, "audit.channel_id": channel_id}})
        
    elif update_type == "addAuditor":
        auditor_id = int(data.get("auditorId"))
        settings = await func.get_settings(guild_id)
        auditors = settings.get("audit", {}).get("auditors", [])
        if auditor_id not in auditors:
            auditors.append(auditor_id)
            await func.update_settings(guild_id, {"$set": {"audit.auditors": auditors}})
            
    elif update_type == "removeAuditor":
        auditor_id = int(data.get("auditorId"))
        settings = await func.get_settings(guild_id)
        auditors = settings.get("audit", {}).get("auditors", [])
        if auditor_id in auditors:
            auditors.remove(auditor_id)
            await func.update_settings(guild_id, {"$set": {"audit.auditors": auditors}})
    
    return {
        "op": "updateAuditSettings",
        "status": "success",
        "guildId": str(guild_id),
        "userId": str(user_id)
    }

async def getAnnounceSettings(bot: commands.Bot, data: Dict) -> Dict:
    """Get announce settings for a guild (roles that can use announce)"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return error_msg("Could not verify your membership.", user_id=user_id, level="error")
    
    # Check permission - only admins can view/change these settings
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    if not member.guild_permissions.administrator and user_id not in bot_access_users:
        return error_msg("You don't have permission to view announce settings.", user_id=user_id, level="error")
    
    settings = await func.get_settings(guild_id)
    announce_roles = settings.get("announce_roles", [])
    
    # Get role details
    roles_data = []
    for role_id in announce_roles:
        role = guild.get_role(role_id)
        if role:
            roles_data.append({
                "id": str(role.id),
                "name": role.name,
                "color": str(role.color)
            })
    
    # Get all available roles (excluding @everyone and bot roles)
    available_roles = []
    for role in guild.roles:
        if role.name != "@everyone" and not role.is_bot_managed():
            available_roles.append({
                "id": str(role.id),
                "name": role.name,
                "color": str(role.color)
            })
    
    return {
        "op": "getAnnounceSettings",
        "announceRoles": roles_data,
        "availableRoles": available_roles,
        "guildId": str(guild_id),
        "userId": str(user_id)
    }

async def updateAnnounceSettings(bot: commands.Bot, data: Dict) -> Dict:
    """Update announce settings (add/remove roles)"""
    user_id = int(data.get("userId"))
    guild_id = int(data.get("guildId"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return error_msg("Guild not found.", user_id=user_id, level="error")
    
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return error_msg("Could not verify your membership.", user_id=user_id, level="error")
    
    # Check permission
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    if not member.guild_permissions.administrator and user_id not in bot_access_users:
        return error_msg("You don't have permission to change announce settings.", user_id=user_id, level="error")
    
    action = data.get("action")
    role_id = int(data.get("roleId")) if data.get("roleId") else None
    
    settings = await func.get_settings(guild_id)
    announce_roles = settings.get("announce_roles", [])
    
    if action == "add" and role_id:
        if role_id not in announce_roles:
            announce_roles.append(role_id)
            await func.update_settings(guild_id, {"$set": {"announce_roles": announce_roles}})
            
    elif action == "remove" and role_id:
        if role_id in announce_roles:
            announce_roles.remove(role_id)
            await func.update_settings(guild_id, {"$set": {"announce_roles": announce_roles}})
    
    return {
        "op": "updateAnnounceSettings",
        "status": "success",
        "guildId": str(guild_id),
        "userId": str(user_id)
    }

async def forceSync(bot: commands.Bot, data: Dict) -> Dict:
    """Force sync slash commands"""
    user_id = int(data.get("userId"))
    
    # Check if user has access
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    user = bot.get_user(user_id)
    if not user:
        try:
            user = await bot.fetch_user(user_id)
        except:
            user = None
    is_owner = await bot.is_owner(user) if user else False
    
    if user_id not in bot_access_users and not is_owner:
        return error_msg("You don't have permission to force sync commands.", user_id=user_id, level="error")
    
    try:
        from sync_manager import smart_sync, get_sync_status
        
        status = get_sync_status(bot)
        
        if not status["can_sync_global"]:
            return {
                "op": "forceSync",
                "status": "cooldown",
                "cooldown": status["global_cooldown_remaining"],
                "msg": f"⏳ Global sync on cooldown. Try again in {status['global_cooldown_remaining']}s",
                "userId": str(user_id)
            }
        
        result = await smart_sync(bot, force=True)
        
        if result["synced"]:
            return {
                "op": "forceSync",
                "status": "success",
                "count": result["count"],
                "msg": f"✅ {result['reason']}",
                "userId": str(user_id)
            }
        else:
            return {
                "op": "forceSync",
                "status": "skipped",
                "msg": result["reason"],
                "userId": str(user_id)
            }
    except Exception as e:
        return error_msg(f"Sync failed: {str(e)}", user_id=user_id, level="error")

async def getSessions(bot: commands.Bot, data: Dict) -> Dict:
    """Get all saved sessions"""
    user_id = int(data.get("userId"))
    
    # Check permission - strict, only for bot owner or admins involved in debugging
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    user = bot.get_user(user_id)
    if not user:
        try:
            user = await bot.fetch_user(user_id)
        except:
            user = None
    is_owner = await bot.is_owner(user) if user else False
    
    if user_id not in bot_access_users and not is_owner:
        return error_msg("You don't have permission to view sessions.", user_id=user_id, level="error")

    cursor = func.MONGO_DB[func.settings.mongodb_name]["sessions"].find({})
    sessions = []
    async for session in cursor:
        sessions.append({
            "id": str(session["_id"]),
            "guild_id": session.get("guild_id"),
            "channel_id": session.get("channel_id"),
            "track_count": len(session.get("queue", []))
        })
        
    return {
        "op": "getSessions",
        "sessions": sessions,
        "userId": str(user_id)
    }

async def clearSessions(bot: commands.Bot, data: Dict) -> Dict:
    """Clear all saved sessions"""
    user_id = int(data.get("userId"))
    
    # Check permission
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    is_owner = await bot.is_owner(bot.get_user(user_id))
    
    if user_id not in bot_access_users and not is_owner:
        return error_msg("You don't have permission to clear sessions.", user_id=user_id, level="error")
        
    await func.MONGO_DB[func.settings.mongodb_name]["sessions"].delete_many({})
    
    return {
        "op": "clearSessions",
        "status": "success",
        "msg": "All sessions cleared!",
        "userId": str(user_id)
    }

async def deleteSession(bot: commands.Bot, data: Dict) -> Dict:
    """Delete a specific session"""
    user_id = int(data.get("userId"))
    
    # Check permission
    bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
    is_owner = await bot.is_owner(bot.get_user(user_id))
    
    if user_id not in bot_access_users and not is_owner:
        return error_msg("You don't have permission to delete sessions.", user_id=user_id, level="error")
        
    session_id = data.get("sessionId")
    if not session_id:
        return error_msg("Session ID required.", user_id=user_id, level="error")
        
    from bson.objectid import ObjectId
    try:
        await func.MONGO_DB[func.settings.mongodb_name]["sessions"].delete_one({"_id": ObjectId(session_id)})
        return {
            "op": "deleteSession",
            "status": "success",
            "sessionId": session_id,
            "msg": "Session deleted!",
            "userId": str(user_id)
        }
    except Exception as e:
        return error_msg(f"Failed to delete session: {e}", user_id=user_id, level="error")

METHODS: Dict[str, Union[SystemMethod, PlayerMethod]] = {
    "initBot": SystemMethod(initBot, credit=0),
    "initUser": SystemMethod(initUser, credit=2),
    "getPlaylist": SystemMethod(getPlaylist),
    "updatePlaylist": SystemMethod(updatePlaylist, credit=2),
    "getMutualGuilds": SystemMethod(getMutualGuilds),
    "getSettings": SystemMethod(getSettings),
    "getLyrics": SystemMethod(getLyrics),
    "updateSettings": SystemMethod(updateSettings),
    "getRecommendation": SystemMethod(getRecommendation, credit=5),
    "closeConnection": SystemMethod(closeConnection, credit=0),
    "getTracks": SystemMethod(getTracks, credit=5),
    "initPlayer": PlayerMethod(initPlayer),
    "skipTo": PlayerMethod(skipTo),
    "backTo": PlayerMethod(backTo),
    "moveTrack": PlayerMethod(moveTrack),
    "addTracks": PlayerMethod(addTracks, auto_connect=True),
    "shuffleTrack": PlayerMethod(shuffleTrack, credit=3),
    "repeatTrack": PlayerMethod(repeatTrack),
    "removeTrack": PlayerMethod(removeTrack),
    "clearQueue": PlayerMethod(clearQueue),
    "updateVolume": PlayerMethod(updateVolume, credit=2),
    "updatePause": PlayerMethod(updatePause),
    "updatePosition": PlayerMethod(updatePosition),
    "toggleAutoplay": PlayerMethod(toggleAutoplay),
    "updateFilter": PlayerMethod(updateFilter),
    "searchAndPlay": PlayerMethod(searchAndPlay, credit=5, auto_connect=True),
    # Dashboard extended methods
    "getGuildChannels": SystemMethod(getGuildChannels),
    "sendAnnounce": SystemMethod(sendAnnounce, credit=2),
    "getAnnounceSettings": SystemMethod(getAnnounceSettings),
    "updateAnnounceSettings": SystemMethod(updateAnnounceSettings, credit=2),
    "getAuditSettings": SystemMethod(getAuditSettings),
    "updateAuditSettings": SystemMethod(updateAuditSettings, credit=2),
    "forceSync": SystemMethod(forceSync, credit=10),
    "getSessions": SystemMethod(getSessions),
    "clearSessions": SystemMethod(clearSessions, credit=2),
    "deleteSession": SystemMethod(deleteSession, credit=2)
}

async def process_methods(ipc_client, bot: commands.Bot, data: Dict) -> None:
    op: str = data.get("op", "")
    method = METHODS.get(op)
    
    user_id_str = data.get("userId")
    if not user_id_str:
        return
        
    user_id = int(user_id_str)
    
    if not method:
        func.logger.warning(f"IPC: Unknown operation '{op}' from user {user_id}")
        return

    # Ratelimit check
    if user_id not in RATELIMIT_COUNTER or (time.time() - RATELIMIT_COUNTER[user_id]["time"]) >= 300:
        RATELIMIT_COUNTER[user_id] = {"time": time.time(), "count": 0}
    else:
        if RATELIMIT_COUNTER[user_id]["count"] >= 100:
            return await ipc_client.send({"op": "rateLimited", "userId": str(user_id)})
        RATELIMIT_COUNTER[user_id]["count"] += method.credit

    try:
        env: Dict = {"bot": bot, "data": data}
        args: List = []
        
        params = method.params
        # If it's a PlayerMethod or SystemMethod that needs guild/member context
        if not (type(method) == SystemMethod):
            guild_id_str = data.get("guildId")
            if guild_id_str:
                guild = bot.get_guild(int(guild_id_str))
                if guild:
                    env["guild"] = guild
                    env["member"] = guild.get_member(user_id) or await guild.fetch_member(user_id)
            else:
                user = bot.get_user(user_id)
                if not user:
                    try:
                        user = await bot.fetch_user(user_id)
                    except Exception:
                        return await ipc_client.send(error_msg("Could not locate user. Try sending a message in a server first.", user_id=user_id))
                
                # Find the user in mutual guilds to get a member object
                found_mutual = False
                for guild in user.mutual_guilds:
                    member = guild.get_member(user_id)
                    if member and member.voice and member.voice.channel:
                        env["guild"] = guild
                        env["member"] = member
                        found_mutual = True
                        break
                
                if not found_mutual:
                    # Fallback: Search all guilds manually (robust voice state check)
                    for guild in bot.guilds:
                        if user_id in guild.voice_states:
                             member = guild.get_member(user_id)
                             if not member:
                                 try: 
                                     member = await guild.fetch_member(user_id)
                                 except: 
                                     continue
                             
                             if member and member.voice and member.voice.channel:
                                 env["guild"] = guild
                                 env["member"] = member
                                 break
            
            # Final check for required parameters
            if "member" in params and "member" not in env:
                # If we have a guild but no member (e.g. guildId provided but user not found/not in voice)
                if guild := env.get("guild"):
                    try:
                        env["member"] = guild.get_member(user_id) or await guild.fetch_member(user_id)
                    except:
                        pass
                
                if "member" not in env:
                    return await ipc_client.send(error_msg("You need to be in a voice channel or specify a valid guild!", user_id=user_id))
            
            if "player" in params:
                guild = env.get("guild")
                member = env.get("member")
                
                if not guild:
                    return await ipc_client.send(error_msg("Could not determine the server context for this player command.", user_id=user_id))
                
                player = guild.voice_client
                if not player:
                    if not method.auto_connect or not member or not member.voice:
                        return await ipc_client.send(error_msg("The bot is not connected to a voice channel in this server.", user_id=user_id))
                    
                    # Attempt to auto-connect
                    player = await connect_channel(member, bot)
                    if not player:
                        return await ipc_client.send(error_msg("Failed to connect the bot to your voice channel.", user_id=user_id))

                # Check if user is in the same voice channel as the player
                if member and member.voice and member.voice.channel:
                    if player.channel.id != member.voice.channel.id:
                        # Some commands might be allowed from different channels if privileged, 
                        # but usually music bots require same channel.
                        # For now, we'll keep the same restriction or use is_privileged.
                        if not player.is_privileged(member):
                            return await ipc_client.send(error_msg("You must be in the same voice channel as the bot!", user_id=user_id))
                
                env["player"] = player
        
        # Prepare arguments based on method's expected parameters
        for param in params:
            args.append(env.get(param))
            
        # Execute the method
        if resp := await method.function(*args):
            await ipc_client.send(resp)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await ipc_client.send(error_msg(f"An internal error occurred: {str(e)}", user_id=user_id, level="error"))