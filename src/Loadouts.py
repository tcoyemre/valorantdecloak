import time
import requests
from colr import color
from src.constants import sockets, hide_names
import json


class Loadouts:
    def __init__(self, Requests, log, colors, Server, current_map):

        self.Requests = Requests
        self.log = log
        self.colors = colors
        self.Server = Server
        self.current_map = current_map

    def get_self_loadout(self):
        """Fetch the current player's own loadout (available in menus too) and
        return a weapons dict in the same shape the web panel expects:
        { weapon_uuid: {weapon, skinDisplayName, skinDisplayIcon, buddy_displayIcon} }
        """
        resp = self.Requests.fetch(
            "pd",
            f"/personalization/v2/players/{self.Requests.puuid}/playerloadout",
            "get",
        )
        try:
            loadout = resp.json()
        except Exception:
            return None
        if not isinstance(loadout, dict) or "Guns" not in loadout:
            return None

        # Cache the valorant-api lookups on the instance so menu refreshes are cheap.
        if not hasattr(self, "_valApiWeaponsData"):
            self._valApiWeaponsData = requests.get(
                "https://valorant-api.com/v1/weapons").json().get("data", [])
            self._valApiBuddiesData = requests.get(
                "https://valorant-api.com/v1/buddies").json().get("data", [])

        weapons = {}
        for gun in loadout.get("Guns", []):
            weapon_id = str(gun.get("ID", "")).lower()
            if not weapon_id:
                continue
            entry = {}
            for weapon in self._valApiWeaponsData:
                if weapon["uuid"].lower() != weapon_id:
                    continue
                entry["weapon"] = weapon["displayName"]
                for skin in weapon["skins"]:
                    if skin["uuid"].lower() != str(gun.get("SkinID", "")).lower():
                        continue
                    entry["skinDisplayName"] = skin["displayName"]
                    icon = None
                    for chroma in skin["chromas"]:
                        if chroma["uuid"].lower() == str(gun.get("ChromaID", "")).lower():
                            icon = chroma["displayIcon"] or chroma["fullRender"] or skin["displayIcon"]
                    if icon is None:
                        icon = skin["displayIcon"]
                    if icon is None and skin.get("levels"):
                        icon = skin["levels"][0]["displayIcon"]
                    if skin["displayName"].startswith("Standard") or skin["displayName"].startswith("Melee"):
                        icon = weapon["displayIcon"]
                    entry["skinDisplayIcon"] = icon
                    break
                break
            charm_id = str(gun.get("CharmID", "")).lower()
            if charm_id:
                for buddy in self._valApiBuddiesData:
                    if buddy["uuid"].lower() == charm_id:
                        entry["buddy_displayIcon"] = buddy["displayIcon"]
                        break
            if entry:
                weapons[weapon_id] = entry
        return weapons

    def get_match_loadouts(self, match_id, players, weaponChoose, valoApiSkins, names, state="game"):
        playersBackup = players
        weaponLists = {}
        valApiWeapons = requests.get(
            "https://valorant-api.com/v1/weapons").json()
        if state == "game":
            team_id = "Blue"
            PlayerInventorys = self.Requests.fetch(
                "glz", f"/core-game/v1/matches/{match_id}/loadouts", "get")
        elif state == "pregame":
            pregame_stats = players
            players = players["AllyTeam"]["Players"]
            team_id = pregame_stats['Teams'][0]['TeamID']
            PlayerInventorys = self.Requests.fetch(
                "glz", f"/pregame/v1/matches/{match_id}/loadouts", "get")

        # subject (player UUID) -> loadout lookup
        loadout_by_subject = {}
        for loadout_entry in PlayerInventorys["Loadouts"]:
            subj = loadout_entry.get("Subject", "").lower()
            # if player has an agent != spectator
            char_id = loadout_entry.get("CharacterID", "")
            if subj and char_id:
                loadout_by_subject[subj] = loadout_entry["Loadout"] if state == "game" else loadout_entry

        for player in players:
            subj = player.get("Subject", "").lower()
            inv = loadout_by_subject.get(subj)
            if inv is None:
                continue
            for weapon in valApiWeapons["data"]:
                if weapon["displayName"].lower() == weaponChoose.lower():
                    skin_id = \
                        inv["Items"][weapon["uuid"].lower()]["Sockets"]["bcef87d6-209b-46c6-8b19-fbe40bd95abc"]["Item"][
                            "ID"]
                    json_data = valoApiSkins.json()

                    if "data" not in json_data:
                        self.log("Skins API response missing 'data'.")
                        return None

                    for skin in json_data["data"]:
                        if skin_id.lower() == skin["uuid"].lower():
                            rgb_color = self.colors.get_rgb_color_from_skin(
                                skin["uuid"].lower(), valoApiSkins)
                            skin_display_name = skin["displayName"].replace(
                                f" {weapon['displayName']}", "")
                            # if rgb_color is not None:
                            weaponLists.update({player["Subject"]: color(
                                skin_display_name, fore=rgb_color)})
                            # else:
                            #     weaponLists.update({player["Subject"]: color(skin["Name"], fore=rgb_color)})
        final_json = self.convertLoadoutToJsonArray(
            PlayerInventorys, playersBackup, state, names)
        # self.log(f"json for website: {final_json}")
        self.Server.send_payload("matchLoadout", final_json)
        return [weaponLists, final_json]

    # this will convert valorant loadouts to json with player names
    def convertLoadoutToJsonArray(self, PlayerInventorys, players, state, names):
        # get agent dict from main in future
        # names = self.namesClass.get_names_from_puuids(players)
        valoApiSprays = requests.get("https://valorant-api.com/v1/sprays")
        valoApiWeapons = requests.get("https://valorant-api.com/v1/weapons")
        valoApiBuddies = requests.get("https://valorant-api.com/v1/buddies")
        valoApiAgents = requests.get("https://valorant-api.com/v1/agents")
        valoApiTitles = requests.get(
            "https://valorant-api.com/v1/playertitles")
        valoApiPlayerCards = requests.get(
            "https://valorant-api.com/v1/playercards")

        final_final_json = {"Players": {},
                            "time": int(time.time()),
                            "map": self.current_map}

        final_json = final_final_json["Players"]
        if state == "game":
            PlayerInventorys = PlayerInventorys["Loadouts"]

            # subject (player UUID) -> loadout lookup
            loadout_by_subject = {}
            for entry in PlayerInventorys:
                subj = entry.get("Subject", "").lower()
                # if player has an agent != spectator
                char_id = entry.get("CharacterID", "")
                if subj and char_id:
                    loadout_by_subject[subj] = entry["Loadout"]

            for player in players:
                subject = player["Subject"]
                subj = subject.lower()
                loadout_entry = loadout_by_subject.get(subj)

                final_json.update(
                    {
                        subject: {}
                    }
                )

                # skip if not found
                if loadout_entry is None:
                    continue

                PlayerInventory = loadout_entry

                # creates name field - always show player name
                final_json[subject].update({"Name": names[subject]})

                # creates team field
                final_json[subject].update({"Team": player["TeamID"]})

                # create spray field
                final_json[subject].update({"Sprays": {}})
                # append sprays to field

                final_json[subject].update(
                    {"Level": player["PlayerIdentity"]["AccountLevel"]})

                for title in valoApiTitles.json()["data"]:
                    if title["uuid"] == player["PlayerIdentity"]["PlayerTitleID"]:
                        final_json[subject].update(
                            {"Title": title["titleText"]})

                for PCard in valoApiPlayerCards.json()["data"]:
                    if PCard["uuid"] == player["PlayerIdentity"]["PlayerCardID"]:
                        final_json[subject].update(
                            {"PlayerCard": PCard["largeArt"]})

                for agent in valoApiAgents.json()["data"]:
                    if agent["uuid"] == player["CharacterID"]:
                        final_json[subject].update(
                            {"AgentArtworkName": agent["displayName"] + "Artwork"})
                        final_json[subject].update(
                            {"Agent": agent["displayIcon"]})

                spray_selections = [
                    s for s in PlayerInventory.get("Expressions", {}).get("AESSelections", [])
                    if s.get("TypeID") == "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475"
                ]
                for j, spray in enumerate(spray_selections):
                    final_json[subject]["Sprays"].update({j: {}})
                    for sprayValApi in valoApiSprays.json()["data"]:
                        if spray["AssetID"].lower() == sprayValApi["uuid"].lower():
                            final_json[subject]["Sprays"][j].update({
                                "displayName": sprayValApi["displayName"],
                                "displayIcon": sprayValApi["displayIcon"],
                                "fullTransparentIcon": sprayValApi["fullTransparentIcon"]
                            })

                # create weapons field
                final_json[subject].update({"Weapons": {}})

                for skin in PlayerInventory["Items"]:

                    # create skin field
                    final_json[subject]["Weapons"].update({skin: {}})

                    for socket in PlayerInventory["Items"][skin]["Sockets"]:
                        # predefined sockets
                        for var_socket in sockets:
                            if socket == sockets[var_socket]:
                                final_json[subject]["Weapons"][skin].update(
                                    {
                                        var_socket: PlayerInventory["Items"][skin]["Sockets"][socket]["Item"]["ID"]
                                    }
                                )

                    # create buddy field
                    # self.log("predefined sockets")
                    # final_json[subject]["Weapons"].update({skin: {}})

                    # buddies
                    for socket in PlayerInventory["Items"][skin]["Sockets"]:
                        if sockets["skin_buddy"] == socket:
                            for buddy in valoApiBuddies.json()["data"]:
                                if buddy["uuid"] == PlayerInventory["Items"][skin]["Sockets"][socket]["Item"]["ID"]:
                                    final_json[subject]["Weapons"][skin].update(
                                        {
                                            "buddy_displayIcon": buddy["displayIcon"]
                                        }
                                    )

                    # append names to field
                    for weapon in valoApiWeapons.json()["data"]:
                        if skin == weapon["uuid"]:
                            final_json[subject]["Weapons"][skin].update(
                                {
                                    "weapon": weapon["displayName"]
                                }
                            )
                            for skinValApi in weapon["skins"]:
                                if skinValApi["uuid"] == PlayerInventory["Items"][skin]["Sockets"][sockets["skin"]]["Item"]["ID"]:
                                    final_json[subject]["Weapons"][skin].update(
                                        {
                                            "skinDisplayName": skinValApi["displayName"]
                                        }
                                    )
                                    for chroma in skinValApi["chromas"]:
                                        if chroma["uuid"] == PlayerInventory["Items"][skin]["Sockets"][sockets["skin_chroma"]]["Item"]["ID"]:
                                            if chroma["displayIcon"] != None:
                                                final_json[subject]["Weapons"][skin].update(
                                                    {
                                                        "skinDisplayIcon": chroma["displayIcon"]
                                                    }
                                                )
                                            elif chroma["fullRender"] != None:
                                                final_json[subject]["Weapons"][skin].update(
                                                    {
                                                        "skinDisplayIcon": chroma["fullRender"]
                                                    }
                                                )
                                            elif skinValApi["displayIcon"] != None:
                                                final_json[subject]["Weapons"][skin].update(
                                                    {
                                                        "skinDisplayIcon": skinValApi["displayIcon"]
                                                    }
                                                )
                                            else:
                                                final_json[subject]["Weapons"][skin].update(
                                                    {
                                                        "skinDisplayIcon": skinValApi["levels"][0]["displayIcon"]
                                                    }
                                                )
                                    if skinValApi["displayName"].startswith("Standard") or skinValApi["displayName"].startswith("Melee"):
                                        final_json[subject]["Weapons"][skin]["skinDisplayIcon"] = weapon["displayIcon"]

        return final_final_json
