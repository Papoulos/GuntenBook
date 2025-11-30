<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Gutenprint

Une application web pour rechercher des livres sur le Projet Gutenberg, visualiser leur contenu HTML et les convertir en PDF.

## Exécution locale

### Prérequis
- Node.js
- Python 3

### Installation

1.  **Installer les dépendances du frontend :**
    ```bash
    npm install
    ```

2.  **Installer les dépendances du backend :**
    ```bash
    pip install -r requirements.txt
    ```

### Démarrage de l'application

Pour démarrer à la fois le serveur de développement frontend et le serveur backend Flask, exécutez la commande suivante :

```bash
npm start
```

Cela lancera :
- Le serveur frontend Vite sur `http://localhost:3001`
- Le serveur backend Flask sur `http://localhost:5001`

L'application devrait s'ouvrir automatiquement dans votre navigateur. Si ce n'est pas le cas, vous pouvez y accéder manuellement à l'adresse `http://localhost:3001`.
