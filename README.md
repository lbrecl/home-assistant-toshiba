# Toshiba Legacy TV pour Home Assistant

Pilote les anciens téléviseurs Toshiba dotés de l’API locale **IPC v2 / PIN_Auth**, sans l’application mobile Toshiba obsolète. L’appairage se fait directement dans l’interface Home Assistant : adresse IP, puis code PIN affiché par la TV.

Première version expérimentale. Le protocole a été vérifié sur un **Toshiba 46TL938K**, firmware **7.0.28.16.1**. La compatibilité d’autres modèles reste à confirmer. Cette intégration ne cible pas Android TV, Fire TV, VIDAA ou Vestel SmartCenter.

## Installation depuis le Marketplace

Home Assistant **2026.11 ou ultérieur** :

1. Ouvrir **Paramètres → Marketplace → Ajouter depuis un lien**.
2. Ajouter `https://github.com/lbrecl/home-assistant-toshiba` comme intégration. La connexion GitHub demandée par le Marketplace sert à lire le dépôt public.
3. Ouvrir la fiche **Toshiba Legacy TV**, puis choisir **Installer**. Redémarrer Home Assistant si demandé.
4. Aller dans **Paramètres → Appareils et services → Ajouter une intégration → Toshiba Legacy TV**.
5. Allumer la TV, saisir son adresse IP et son port HTTP (généralement `8080`).
6. Saisir immédiatement le PIN à quatre chiffres affiché sur l’écran. Si le code a expiré, cocher **Relancer l’appairage**, valider, puis saisir le nouveau code.

Il s’agit d’un dépôt personnalisé, pas d’une intégration référencée par défaut dans le catalogue. Aucun fichier YAML à modifier et aucun accès au NAS nécessaire pour l’installation par le Marketplace.

### Sur la TV

Selon le modèle : **Réglage → Préférences → Réglage du périphérique réseau → Réglages périphérique externe → Profil de commande des Apps → Détection d’un nouvel appareil → Activé**. Les noms de menus peuvent varier. La TV doit être allumée et accessible depuis Home Assistant pendant l’appairage.

### Commande marche TV et veille active

Pour activer la veille réseau sur la série TL938 : **Réglage → Préférences → Réglage du périphérique réseau → Commande marche TV → Activé**. Attendre au moins une dizaine de secondes après la mise en veille avant de tester une commande. Cette veille active consomme davantage que la veille normale.

La [notice Toshiba TL938, rubrique « Commande marche TV »](https://www.notice-facile.com/notice/77977/toshiba%2Btl938-_f) décrit cette fonction pour une connexion **Wi-Fi**. Elle ne constitue pas une garantie de réveil par Ethernet pour tous les modèles.

**Essai en Ethernet sur le 46TL938K de référence :** après activation du réglage, l’API HTTP/HTTPS a répondu en veille. Lors d’un second cycle, elle répondait encore après 20 secondes, sans nouvel envoi de paquet Wake-on-LAN. Une touche Marche a fait passer l’état API de `off` à `on`, mais l’utilisateur a constaté que **l’écran restait éteint**. Le premier essai avait également inclus des paquets Wake-on-LAN : leur contribution au retour du réseau n’est pas établie.

**Un port réseau joignable, une commande acceptée ou un état API `on` ne prouvent donc pas le réveil physique de l’écran.** Celui-ci reste non validé. La version actuelle n’annonce pas de commande Marche discrète et n’envoie pas de paquets Wake-on-LAN. Utiliser la télécommande physique pour allumer la TV tant que le réveil réel n’a pas été confirmé sur son modèle. Le lecteur multimédia affiche l’état déclaré par l’API ; il peut différer de l’état visible de l’écran.

### Installation manuelle

Copier `custom_components/toshiba_legacy` dans le dossier `custom_components` de la configuration Home Assistant, puis redémarrer et ajouter l’intégration.

## Entités et commandes

- Un **lecteur multimédia** : état réel, entrée courante, volume +/− et mise en veille lorsque l’état allumé est confirmé.
- Une **télécommande** utilisable avec `remote.send_command`.
- Des **boutons** : bascule marche/veille, sourdine, sources, navigation, OK, retour, menu, quitter et informations.
- État interrogé toutes les 15 secondes. Une TV injoignable est indiquée **indisponible**, sans présumer son état.

Les noms de commandes sont : `power`, `volume_up`, `volume_down`, `mute`, `up`, `down`, `left`, `right`, `ok`, `back`, `exit`, `menu`, `info`, `input`, `channel_up`, `channel_down`, et les chiffres `0` à `9`.

Exemple d’action (remplacer l’identifiant de l’entité par celui créé chez vous) :

```yaml
action: remote.send_command
target:
  entity_id: remote.toshiba_tl938k_telecommande
data:
  command: volume_up
```

Plusieurs commandes peuvent être envoyées en liste. Maximum : 30 commandes, 10 répétitions et 5 secondes entre les touches. L’appui maintenu n’est pas pris en charge.

## Limites connues

- **Réveil physique non validé**, y compris après activation de « Commande marche TV ». L’API peut rester accessible et déclarer `on` sans que l’écran s’allume : voir la rubrique veille active ci-dessus. Le bouton marche/veille envoie une **bascule** ; son effet physique doit être vérifié sur le téléviseur.
- **Pas de curseur de volume ni d’état de sourdine** : le firmware de référence ne fournit pas ces informations. La sourdine est une bascule par touche.
- Les touches sont basées sur la table de télécommande européenne. L’API a accepté les touches Informations et Quitter ; toutes les touches n’ont pas été confirmées visuellement.
- La lecture d’état et la sélection directe de `HDMI_2` ont été vérifiées. Cette version expose le bouton Sources pour naviguer avec la télécommande ; elle n’invente pas de liste d’entrées disponibles.
- L’état est vérifié avant l’envoi de la bascule de mise en veille. Un changement simultané via une autre télécommande peut toutefois créer une course entre la lecture et la commande.
- Le PIN n’est pas conservé. Les identifiants délivrés par la TV sont stockés par Home Assistant dans son entrée de configuration, jamais dans ce dépôt. Le pilotage se fait en HTTP local avec authentification Digest ; la TV n’est pas un service cloud.

## Vérification et développement

```sh
python -m pip install homeassistant==2026.11.1 pytest pytest-asyncio ruff
ruff check .
python -m pytest -q
```

Les tests couvrent la dérivation du mot de passe, les erreurs d’authentification, le transport HTTP Digest, les refus de commande et le parcours de configuration Home Assistant. Ils utilisent des données synthétiques, jamais les identifiants d’un téléviseur personnel. Les vérifications matérielles décrites ci-dessus ont été faites séparément sur la TV de référence. L’installation par le Marketplace doit encore être confirmée après publication.

## Références

- [9SQ/regza-digest-auth](https://github.com/9SQ/regza-digest-auth) : référence de l’appairage PIN, PBKDF2-SHA1 (1331 itérations), AES-128-CBC et Digest.
- [DSchndr/toshiba-stv-ip-remote](https://github.com/DSchndr/toshiba-stv-ip-remote) : documentation de l’API Toshiba et table des touches.
- [Documentation du Marketplace](https://www.home-assistant.io/integrations/marketplace/).

Projet communautaire, sans affiliation à Toshiba ou Home Assistant. Licence MIT.
