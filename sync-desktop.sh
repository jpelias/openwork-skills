#!/bin/bash
# sync-desktop.sh — Copia config completa de equipo local a remoto
# XFCE + MATE + LightDM + chrony + APT + paquetes básicos
# Uso: ./sync-desktop.sh <user@ip>
# Ej:   ./sync-desktop.sh usuario@192.168.18.24

set -e

TARGET="${1:?Uso: $0 <user@ip>}"
REMOTE_USER="${TARGET%@*}"
REMOTE_IP="${TARGET#*@}"

[ -z "$REMOTE_USER" ] && { echo "ERROR: usuario remoto vacío"; exit 1; }
[ -z "$REMOTE_IP"   ] && { echo "ERROR: IP remota vacía";   exit 1; }

# ── Paquetes base que deben estar instalados en ambos ──────────────────
BASE_PACKAGES="wget mc rar unrar chrony htop curl git unzip zip p7zip-full rsync neofetch btop nano"

echo "============================================"
echo " sync-desktop → $TARGET"
echo "============================================"

# ── 1. Verificar conectividad ──────────────────────────────────────────
echo "[1/13] Verificando conectividad..."
ssh -o ConnectTimeout=5 "root@$REMOTE_IP" hostname > /dev/null 2>&1 || {
    echo "ERROR: no se puede conectar como root a $REMOTE_IP"
    exit 1
}

# ── 2. Detectar monitor remoto (ANTES de parar LightDM) ───────────────
echo "[2/13] Detectando monitores..."
LOCAL_MONITOR=$(xrandr --listmonitors 2>/dev/null | grep '^ ' | head -1 | awk '{print $4}' || echo "eDP-1")
LOCAL_XFCONF_MONITOR="monitor${LOCAL_MONITOR//-/}"

REMOTE_MONITOR=$(ssh "$TARGET" "DISPLAY=:0 xrandr --listmonitors 2>/dev/null | grep '^ ' | head -1 | awk '{print \$4}'" 2>/dev/null || echo "")
[ -z "$REMOTE_MONITOR" ] && REMOTE_MONITOR="HDMI-A-0"
REMOTE_XFCONF_MONITOR="monitor${REMOTE_MONITOR//-/}"

echo "  Local:  $LOCAL_MONITOR → $LOCAL_XFCONF_MONITOR"
echo "  Remoto: $REMOTE_MONITOR → $REMOTE_XFCONF_MONITOR"

# ── 3. Cerrar sesión del usuario en el destino ─────────────────────────
echo "[3/13] Cerrando sesión de $REMOTE_USER en destino..."
ssh "root@$REMOTE_IP" "loginctl terminate-user $REMOTE_USER" 2>/dev/null || true
ssh "root@$REMOTE_IP" "systemctl stop lightdm" 2>/dev/null || true
sleep 2

# ── 4. Paquetes base ───────────────────────────────────────────────────
echo "[4/13] Instalando paquetes base en destino..."
ssh "root@$REMOTE_IP" "apt-get update -qq && apt-get install -y -qq $BASE_PACKAGES" 2>&1 | tail -3
# ── 5. APT sources ─────────────────────────────────────────────────────
echo "[5/13] Sincronizando APT sources..."

# Backup del sources.list.d remoto antes de borrar
ssh "root@$REMOTE_IP" "cp -a /etc/apt/sources.list.d /etc/apt/sources.list.d.bak 2>/dev/null" || true
ssh "root@$REMOTE_IP" "rm -rf /etc/apt/sources.list.d/*"

scp /etc/apt/sources.list "root@$REMOTE_IP:/etc/apt/sources.list" 2>/dev/null

# Copiar fuentes extra si existen (docker, zerotier, vivaldi, etc.)
for f in /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
    [ -f "$f" ] && scp "$f" "root@$REMOTE_IP:/etc/apt/sources.list.d/" 2>/dev/null
done

# Restaurar backup si no se copió nada
ssh "root@$REMOTE_IP" '
if [ -z \"\$(ls -A /etc/apt/sources.list.d/ 2>/dev/null)\" ]; then
    echo \"WARN: sin sources, restaurando backup\"
    rm -rf /etc/apt/sources.list.d
    mv /etc/apt/sources.list.d.bak /etc/apt/sources.list.d
fi
' 2>/dev/null || true
ssh "root@$REMOTE_IP" "rm -rf /etc/apt/sources.list.d.bak" 2>/dev/null || true

# Copiar claves GPG de repos extra
ssh "root@$REMOTE_IP" "mkdir -p /etc/apt/keyrings"
rsync -avz /etc/apt/keyrings/ "root@$REMOTE_IP:/etc/apt/keyrings/" 2>/dev/null || true
rsync -avz /usr/share/keyrings/ "root@$REMOTE_IP:/usr/share/keyrings/" 2>/dev/null || true

ssh "root@$REMOTE_IP" "apt-get update -qq" 2>&1 | tail -1

# ── 6. Chrony ──────────────────────────────────────────────────────────
echo "[6/13] Sincronizando chrony..."
scp /etc/chrony/chrony.conf "root@$REMOTE_IP:/etc/chrony/chrony.conf" 2>/dev/null
rsync -avz /etc/chrony/sources.d/ "root@$REMOTE_IP:/etc/chrony/sources.d/" 2>/dev/null || true
ssh "root@$REMOTE_IP" "systemctl restart chrony 2>/dev/null || systemctl restart chronyd 2>/dev/null" || true

# ── 7. Temas e iconos (TODO) ──────────────────────────────────────────
echo "[7/13] Sincronizando temas e iconos..."
rsync -avz --delete /usr/share/themes/ "root@$REMOTE_IP:/usr/share/themes/" 2>/dev/null || true
rsync -avz --delete /usr/share/icons/ "root@$REMOTE_IP:/usr/share/icons/" 2>/dev/null || true
[ -d ~/.themes ] && rsync -avz --delete ~/.themes/ "root@$REMOTE_IP:/home/$REMOTE_USER/.themes/" 2>/dev/null || true
[ -d ~/.icons  ] && rsync -avz --delete ~/.icons/  "root@$REMOTE_IP:/home/$REMOTE_USER/.icons/"  2>/dev/null || true
# Ajustar dueño de temas locales (rsync se ejecutó como root)
ssh "root@$REMOTE_IP" "chown -R $REMOTE_USER:$REMOTE_USER /home/$REMOTE_USER/.themes /home/$REMOTE_USER/.icons" 2>/dev/null || true

# Reconstruir cachés de iconos en destino
ssh "root@$REMOTE_IP" '
for d in /usr/share/icons/*/; do
    [ -f "$d/index.theme" ] && gtk-update-icon-cache "$d" 2>/dev/null
done
' || true

# ── 8. XFCE ────────────────────────────────────────────────────────────
echo "[8/13] Sincronizando XFCE..."
ssh "root@$REMOTE_IP" "rm -rf /home/$REMOTE_USER/.config/xfce4 /home/$REMOTE_USER/.cache/sessions /home/$REMOTE_USER/.cache/xfdesktop /home/$REMOTE_USER/.cache/thumbnails"
rsync -avz ~/.config/xfce4/ "root@$REMOTE_IP:/home/$REMOTE_USER/.config/xfce4/" 2>/dev/null
rsync -avz ~/.config/gtk-3.0/ "root@$REMOTE_IP:/home/$REMOTE_USER/.config/gtk-3.0/" 2>/dev/null

# ── 9. Renombrar monitor en config ────────────────────────────────────
echo "[9/13] Aplicando nombre de monitor..."
if [ "$LOCAL_XFCONF_MONITOR" != "$REMOTE_XFCONF_MONITOR" ]; then
    echo "  → Renombrando $LOCAL_XFCONF_MONITOR → $REMOTE_XFCONF_MONITOR"
    ssh "root@$REMOTE_IP" \
      "sed -i 's|$LOCAL_XFCONF_MONITOR|$REMOTE_XFCONF_MONITOR|g' \
       /home/$REMOTE_USER/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
else
    echo "  → Mismo monitor, no requiere ajuste"
fi

# Limpiar referencias a imágenes locales (no existen en el destino)
ssh "root@$REMOTE_IP" "
  sed -i 's|<property name=\"last-image\" type=\"string\" value=\".*\"/>|<property name=\"last-image\" type=\"empty\"/>|g' \
    /home/$REMOTE_USER/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
  sed -i 's|<property name=\"image-path\" type=\"string\" value=\".*\"/>|<property name=\"image-path\" type=\"empty\"/>|g' \
    /home/$REMOTE_USER/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
  sed -i 's|<property name=\"last-single-image\" type=\"string\" value=\".*\"/>|<property name=\"last-single-image\" type=\"empty\"/>|g' \
    /home/$REMOTE_USER/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
"

# ── 10. MATE ────────────────────────────────────────────────────────────
echo "[10/13] Sincronizando MATE..."
dconf dump /org/mate/ > /tmp/mate-sync.dconf
scp /tmp/mate-sync.dconf "$TARGET:/tmp/mate-sync.dconf" 2>/dev/null
ssh "root@$REMOTE_IP" "chown $REMOTE_USER:$REMOTE_USER /tmp/mate-sync.dconf"
ssh "$TARGET" "dconf load /org/mate/ < /tmp/mate-sync.dconf" 2>/dev/null || true

ssh "root@$REMOTE_IP" "mkdir -p /home/$REMOTE_USER/.config/mate /home/$REMOTE_USER/.config/caja"
rsync -avz ~/.config/mate/ "root@$REMOTE_IP:/home/$REMOTE_USER/.config/mate/" 2>/dev/null || true
rsync -avz ~/.config/caja/ "root@$REMOTE_IP:/home/$REMOTE_USER/.config/caja/" 2>/dev/null || true

# ── 11. LightDM ────────────────────────────────────────────────────────
echo "[11/13] Sincronizando LightDM..."
scp /etc/lightdm/lightdm-gtk-greeter.conf "root@$REMOTE_IP:/etc/lightdm/" 2>/dev/null
ssh "root@$REMOTE_IP" "sed -i 's/^greeter-session=.*/greeter-session=lightdm-gtk-greeter/' /etc/lightdm/lightdm.conf"
ssh "root@$REMOTE_IP" "sed -i 's/^user-session=.*/user-session=xfce/' /etc/lightdm/lightdm.conf"

# ── 12. SSH keys ───────────────────────────────────────────────────────
echo "[12/13] Sincronizando claves SSH..."

# usuario
rsync -avz ~/.ssh/ "root@$REMOTE_IP:/home/$REMOTE_USER/.ssh/" 2>/dev/null
ssh "root@$REMOTE_IP" "chown -R $REMOTE_USER:$REMOTE_USER /home/$REMOTE_USER/.ssh && chmod 700 /home/$REMOTE_USER/.ssh && chmod 600 /home/$REMOTE_USER/.ssh/id_rsa 2>/dev/null; chmod 644 /home/$REMOTE_USER/.ssh/id_rsa.pub 2>/dev/null; chmod 600 /home/$REMOTE_USER/.ssh/authorized_keys 2>/dev/null"

# root
ssh "root@$REMOTE_IP" "mkdir -p /root/.ssh"
rsync -avz /root/.ssh/ "root@$REMOTE_IP:/root/.ssh/" 2>/dev/null
ssh "root@$REMOTE_IP" "chmod 700 /root/.ssh && chmod 600 /root/.ssh/id_rsa 2>/dev/null; chmod 644 /root/.ssh/id_rsa.pub 2>/dev/null; chmod 600 /root/.ssh/authorized_keys 2>/dev/null"

# ── 13. Permisos y arranque ───────────────────────────────────────────
echo "[13/13] Ajustando permisos y arrancando..."
ssh "root@$REMOTE_IP" "chown -R $REMOTE_USER:$REMOTE_USER /home/$REMOTE_USER/.config/"
ssh "root@$REMOTE_IP" "systemctl restart lightdm"

rm -f /tmp/mate-sync.dconf

echo ""
echo "============================================"
echo " ✅ Sincronización completa → $TARGET"
echo "    XFCE + MATE + LightDM + chrony + APT + paquetes + SSH"
echo "============================================"
