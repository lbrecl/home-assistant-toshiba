# Toshiba Legacy TV pour Home Assistant

Pilote les anciens téléviseurs Toshiba dotés de l’API locale **IPC v2 / PIN_Auth**, sans l’application mobile Toshiba obsolète. L’appairage se fait directement dans l’interface Home Assistant : adresse IP, puis code PIN affiché par la TV.

Intégration expérimentale. Le protocole a été vérifié sur un **Toshiba 46TL938K**, firmware **7.0.28.16.1**. Cette version utilise la table de touches **CT-90405**, la télécommande de cette série. La compatibilité d’autres modèles et télécommandes reste à confirmer. Cette intégration ne cible pas Android TV, Fire TV, VIDAA ou Vestel SmartCenter.

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

Pour activer la veille réseau sur la série TL938 : **Réglage → Préférences → Réglage du périphérique réseau → Commande marche TV → Activé**. Attendre au moins une dizaine de secondes après la mise en veille avant de tester une commande. Cette veille active consomme davantage que la veille normale. Sur l’exemplaire 46TL938K utilisé pour les essais, l’utilisateur signale aussi que les ports USB restent alimentés avec cette option. Ne pas activer ce mode si les USB doivent s’éteindre en veille ; les essais Wake-on-LAN avec l’option désactivée n’ont pas rétabli l’accès réseau.

La [notice Toshiba TL938, rubrique « Commande marche TV »](https://www.notice-facile.com/notice/77977/toshiba%2Btl938-_f) décrit cette fonction pour une connexion **Wi-Fi**. Elle ne constitue pas une garantie de réveil par Ethernet pour tous les modèles.

**Réveil confirmé en Ethernet sur le 46TL938K**, firmware 7.0.28.16.1, avec ce réglage activé : mise en veille par la touche CT-90405, attente de 20 secondes, état API `off`, envoi du code Marche `40bf12`, puis état `on`. L’utilisateur a confirmé visuellement la mise en veille, le rallumage et le menu affiché après le réveil. Ce cycle n’a utilisé aucun paquet Wake-on-LAN.

**Avec « Commande marche TV » désactivé :** les services HTTP et HTTPS sont restés injoignables après deux essais Wake-on-LAN (ports UDP 7/9, diffusions locale et générale, attentes de 12 puis 30 secondes). Ce test ne valide donc pas un réveil avec les USB éteints. L’intégration ne propose pas de Wake-on-LAN comme solution de remplacement éprouvée sur ce modèle. Si les USB doivent s’éteindre, conserver l’option désactivée et utiliser un autre moyen d’allumage ; la commande réseau seule ne peut pas agir tant que la TV ne répond pas.

Depuis la **version 0.2.0**, `media_player.turn_on` et `remote.turn_on` utilisent ce réveil par API en veille active. Les actions Marche et Veille lisent l’état juste avant l’envoi et n’envoient la touche de bascule que si l’état confirmé est opposé à la demande. Les demandes explicites de puissance sont sérialisées entre le lecteur multimédia et la télécommande. Si l’API ne répond pas, aucune bascule à l’aveugle n’est envoyée.

Cette validation porte sur le modèle et le firmware cités. Sur un autre téléviseur, confirmer aussi le réveil par un affichage visible ; une réponse réseau seule n’est pas suffisante. Le réseau doit rester accessible en veille active. Aucun Wake-on-LAN n’est envoyé et une TV coupée au secteur ne peut pas être réveillée par cette méthode.

### Installation manuelle

Copier `custom_components/toshiba_legacy` dans le dossier `custom_components` de la configuration Home Assistant, puis redémarrer et ajouter l’intégration.

## Entités et commandes

- Un **lecteur multimédia** : état déclaré par la TV, entrée courante, volume +/−, **Marche** et **Veille** avec vérification préalable de l’état.
- Une entité **Télécommande et alimentation TV**, utilisable avec `remote.send_command`, `remote.turn_on` et `remote.turn_off`. Son interrupteur commande la **Marche/Veille de la TV**, pas l’activation du module. La version 0.2.0 corrige l’impossibilité de la remettre sur Marche dans les versions 0.1.x.
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

Pour allumer la TV sans risquer de l’éteindre si elle est déjà allumée, utiliser l’action explicite :

```yaml
action: media_player.turn_on
target:
  entity_id: media_player.toshiba_tl938k
```

Remplacer l’identifiant par celui de votre lecteur. `remote.turn_on` fonctionne aussi avec l’entité de télécommande. Le réseau doit être joignable en veille active. Une mise à jour depuis 0.1.x conserve l’appairage et ne nécessite aucun champ de configuration supplémentaire.

Plusieurs commandes peuvent être envoyées en liste. Maximum : 30 commandes, 10 répétitions et 5 secondes entre les touches. L’appui maintenu n’est pas pris en charge.

## Limites connues

- **Veille active indispensable au réveil par API** : activer « Commande marche TV ». La validation Ethernet concerne le 46TL938K avec le firmware cité. Le bouton marche/veille reste une **bascule** ; pour les automatisations, utiliser `media_player.turn_on` / `turn_off` ou `remote.turn_on` / `turn_off`.
- **Pas de curseur de volume ni d’état de sourdine** : le firmware de référence ne fournit pas ces informations. La sourdine est une bascule par touche.
- Les touches utilisent maintenant la table spécifique **CT-90405**. **MENU a été confirmé visuellement sur le 46TL938K** avec le code `40bf5b`. La table générique utilisée en 0.1.0/0.1.1 envoyait notamment `40bf80`, accepté par l’API mais sans affichage du menu : mettre à jour vers **0.1.2 ou ultérieur**. Toutes les autres touches n’ont pas encore été confirmées visuellement.
- La lecture d’état et l’acceptation de la requête `HDMI_2` ont été vérifiées côté API ; l’effet visible d’un changement réel d’entrée n’a pas encore été confirmé. Cette version expose le bouton Sources pour naviguer avec la télécommande ; elle n’invente pas de liste d’entrées disponibles.
- L’état est vérifié avant l’envoi de la bascule Marche/Veille. Un changement simultané via une autre télécommande peut toutefois créer une course entre la lecture et la commande.
- Le PIN n’est pas conservé. Les identifiants délivrés par la TV sont stockés par Home Assistant dans son entrée de configuration, jamais dans ce dépôt. Le pilotage se fait en HTTP local avec authentification Digest ; la TV n’est pas un service cloud.

## Vérification et développement

```sh
python -m pip install homeassistant==2026.11.1 pytest pytest-asyncio ruff
ruff check .
python -m pytest -q
```

Les tests couvrent la dérivation du mot de passe, les erreurs d’authentification, le transport HTTP Digest, les refus de commande, le parcours de configuration Home Assistant et les commandes Marche/Veille (demandes répétées, demandes simultanées et état devenu inaccessible). Ils utilisent des données synthétiques, jamais les identifiants d’un téléviseur personnel. Les vérifications matérielles décrites ci-dessus ont été faites séparément sur la TV de référence. L’installation par le Marketplace doit encore être confirmée après publication.

## Références

- [9SQ/regza-digest-auth](https://github.com/9SQ/regza-digest-auth) : référence de l’appairage PIN, PBKDF2-SHA1 (1331 itérations), AES-128-CBC et Digest.
- [DSchndr/toshiba-stv-ip-remote](https://github.com/DSchndr/toshiba-stv-ip-remote) : documentation de l’API Toshiba. Sa table générique de touches ne correspond pas entièrement à la CT-90405.
- [Table CT-90405 du noyau Linux](https://github.com/torvalds/linux/blob/master/drivers/media/rc/keymaps/rc-ct-90405.c) : référence des commandes de la télécommande de cette série.
- [Documentation du Marketplace](https://www.home-assistant.io/integrations/marketplace/).

Projet communautaire, sans affiliation à Toshiba ou Home Assistant. Licence MIT.
