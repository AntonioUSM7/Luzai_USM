# Guía de Presentación Remota — LuzAI USM (Tailscale + Túnel SSH)

Checklist rápido para correr todo el proyecto (Frontend, Backend/RAG y Ollama con GPU) en el PC de casa (`antoniolinus`) y mostrarlo desde el notebook en la universidad usando `http://localhost:5173`.

---

## 1. En tu PC de casa (antes de salir)

### 1.1 Verificar que Ollama y Docker estén corriendo
Desde la carpeta del proyecto:
```bash
cd /home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM
docker compose up -d
```

Comprueba que ambos contenedores estén arriba (`luzai_smartguard_frontend` y `luzai_smartguard_backend`) y que el backend responda:
```bash
docker ps
curl http://localhost:8000/api/health
```

### 1.2 Verificar Tailscale SSH
Tailscale ya quedó activo con `--ssh` en este PC (`100.120.111.64`). Para confirmar que está conectado:
```bash
tailscale status
```
*(Si alguna vez reinicias el PC y necesitas asegurarte: `sudo tailscale up --ssh`)*.

### 1.3 Evitar que el PC se suspenda o apague
1. En **Configuración de Energía** del sistema, desactiva la **suspensión automática** cuando esté enchufado a la corriente.
2. Como respaldo adicional por terminal (mantiene el PC despierto por 12 horas; deja esta terminal abierta):
   ```bash
   systemd-inhibit --what=sleep --who="Presentacion LuzAI" --why="Demo remota" sleep 12h
   ```
3. Deja el PC conectado a internet (idealmente por cable Ethernet si tienes).

---

## 2. En tu notebook (en la sala de presentación)

### 2.1 Conectar Tailscale
Asegúrate de que Tailscale esté encendido en el notebook y verifica que alcance a tu PC:
```bash
tailscale ping 100.120.111.64
```

> **Plan B (si el Wi-Fi de la U bloquea Tailscale):**
> Conecta el notebook al **hotspot de tu celular** y vuelve a ejecutar `tailscale ping 100.120.111.64`.

### 2.2 Abrir el túnel SSH
Abre una terminal en el notebook y ejecuta (déjala abierta durante toda la presentación):
```bash
ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 5173:localhost:5173 -L 8000:localhost:8000 antonio@100.120.111.64
```
* `ServerAliveInterval=30` evita que el túnel se congele si pasan minutos sin enviar tráfico mientras hablas.
* Si el comando queda esperando sin errores, el túnel ya está activo.

### 2.3 Abrir la demo en el navegador
En el navegador del notebook entra a:
- **Interfaz principal:** `http://localhost:5173`
- **Health check (opcional, para comprobar conexión rápida):** `http://localhost:8000/api/health`

---

## 3. Si algo falla en vivo (solución rápida)

- **No carga `http://localhost:5173` o se cayó el túnel:**
  1. Revisa la terminal del túnel SSH en el notebook. Si se cerró, vuelve a correr el comando `ssh -N ...`.
  2. Si `tailscale ping 100.120.111.64` falla en el Wi-Fi de la U, pásate al **hotspot del celular**.
- **Error de puerto ocupado en el notebook (`Address already in use`):**
  - Significa que tienes algo corriendo localmente en el puerto `5173` o `8000` en el notebook; detén ese proceso local antes de abrir el túnel.
- **El chat responde lento o da timeout:**
  - Verifica que el túnel siga abierto; si quieres reiniciar los contenedores remotamente sin cerrar sesión:
    ```bash
    ssh antonio@100.120.111.64 "cd /home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM && docker compose restart"
    ```

---

## 4. Al volver a casa (después de presentar)

- Cierra el túnel en el notebook con `Ctrl + C`.
- En tu PC, cierra el `systemd-inhibit` con `Ctrl + C` y vuelve a activar la suspensión automática si la usas normalmente.
