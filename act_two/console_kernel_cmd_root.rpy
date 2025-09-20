# file: game/console_kernel_cmd_root.rpy
# Consola kernel-neutral (tipo Windows CMD) confinada a la carpeta del proyecto (root = un nivel arriba de game/).
# F9 abre, F10 cierra. Compatible con Ren'Py 7.8.x

# ------------------ FLAGS ------------------
define KERNEL_HOST_MODE = False  # False = confinado al proyecto; True = acepta rutas absolutas (peligroso).

# ------------------ Estado UI ------------------
default console_open = False
default console_log = ["Kernel console (CMD-like). Escribe 'help'."]
default console_input = ""
default console_cwd_rel = ""   # "" = raíz de ROOT_BASE

# ------------------ Núcleo ------------------
init -2 python:
    import os, io, time, shutil

    # ---------- RAÍZ: PROYECTO (un nivel arriba de game/) ----------
    PROJECT_DIR = os.path.abspath(os.path.join(config.gamedir, os.pardir))
    ROOT_BASE   = PROJECT_DIR  # raíz efectiva

    # ---------- Helpers ----------
    def _ensure_dir(p):
        try:
            if p and not os.path.isdir(p):
                os.makedirs(p)
        except Exception:
            pass

    def _norm_rel(p): return p.replace("/", "\\")         # para mostrar estilo Windows
    def _unixify(p):  return p.replace("\\", "/")          # para resolver paths

    def _abs_from(rel_or_abs, base_rel):
        """
        Resuelve ruta desde ROOT_BASE.
        - Si KERNEL_HOST_MODE=False: confinado a ROOT_BASE.
        - Si KERNEL_HOST_MODE=True: permite rutas absolutas del sistema (¡peligroso!).
        """
        s = (rel_or_abs or "").strip()
        if KERNEL_HOST_MODE and os.path.isabs(s):
            return os.path.abspath(s)

        base = os.path.abspath(ROOT_BASE)
        if not s:
            target_abs = os.path.abspath(os.path.join(base, _unixify(base_rel)))
        else:
            s_unix = _unixify(s)
            if s_unix.startswith("/"):  # simular "\" = raíz del proyecto
                target_abs = os.path.abspath(os.path.join(base, s_unix.lstrip("/")))
            else:
                target_abs = os.path.abspath(os.path.join(base, _unixify(base_rel), s_unix))

        if KERNEL_HOST_MODE:
            return target_abs

        # Confinamiento al proyecto
        if not (target_abs == base or target_abs.startswith(base + os.sep)):
            return None
        return target_abs

    def _rel_from_abs(abs_path):
        base = os.path.abspath(ROOT_BASE)
        try:
            if abs_path.startswith(base):
                return os.path.relpath(abs_path, base).replace("\\", "/")
        except Exception:
            pass
        return ""

    # ---------- Console I/O ----------
    def console_receive(sender, line):
        # NO sustituir: queremos texto literal
        try:
            s = u"[{}] {}".format(sender, line) if sender else unicode(line)
        except:
            s = "[{}] {}".format(sender, line) if sender else str(line)
        console_log.append(s)
        if len(console_log) > 500:
            del console_log[:-400]

    def _log(line): console_receive(None, line)
    def _ok(msg): _log("OK: " + msg)
    def _err(msg): _log("ERR: " + msg)

    # ---------- API pública para IA ----------
    def kernel_print(sender, text):
        """Escribe una línea en la consola (no ejecuta comandos)."""
        console_receive(sender, text)

    def kernel_exec(line, as_sender=None):
        """Ejecuta un comando como si se tecleara en la consola."""
        console_receive((as_sender + "@" if as_sender else "") + _prompt().rstrip(), line)
        try:
            handle_console_command(line)
        except Exception as e:
            console_receive(None, "ERR: excepción en kernel_exec: %r" % e)

    def kernel_exec_many(text_block, as_sender=None):
        """Ejecuta varias líneas (una por renglón)."""
        for raw in (text_block or "").splitlines():
            cmd = raw.strip()
            if cmd:
                kernel_exec(cmd, as_sender=as_sender)

    # ---------- Prompt ----------
    def _prompt():
        # Muestra C:\project\...
        rel = renpy.store.console_cwd_rel or ""
        shown = "C:\\project" if not rel else "C:\\project\\" + _norm_rel(rel)
        if KERNEL_HOST_MODE:
            shown = "C:\\host" if not rel else "C:\\host\\" + _norm_rel(rel)
        return shown + "> "

    # ---------- Utilidades de FS ----------
    def _list_dir(abs_dir):
        try:
            names = sorted(os.listdir(abs_dir), key=lambda n: (not os.path.isdir(os.path.join(abs_dir,n)), n.lower()))
            return (True, names)
        except Exception as e:
            return (False, repr(e))

    def _fmt_time(ts): return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

    def _print_dir(abs_dir, rel_hint):
        ok, names = _list_dir(abs_dir)
        if not ok: return _err(names)
        root_tag = "C:/host/" if KERNEL_HOST_MODE else "C:/project/"
        _log(" Directorio de " + _norm_rel(root_tag + (rel_hint.strip("/") if rel_hint else "")))
        _log("")
        total = 0
        for n in names:
            full = os.path.join(abs_dir, n)
            st = os.stat(full)
            if os.path.isdir(full):
                _log(" {:<16}    <DIR>          {}".format(_fmt_time(st.st_mtime), n))
            else:
                _log(" {:<16}                {:>8}  {}".format(_fmt_time(st.st_mtime), st.st_size, n))
                total += st.st_size
        _log("               {:>8} bytes".format(total))

    # ---------- Registro de comandos ----------
    COMMANDS = {}
    def command(*names):
        def deco(fn):
            for n in names:
                COMMANDS[n.lower()] = fn
            return fn
        return deco

    @command("help", "?")
    def cmd_help(args):
        _log("Comandos CMD-like (root = carpeta del proyecto):")
        _log("  help / ?                - esta ayuda")
        _log("  cls | clear             - limpia pantalla")
        _log("  time                    - hora actual")
        _log("  pwd                     - muestra directorio actual")
        _log("  cd [ruta] | chdir       - cambia/muestra directorio (\\, ..)")
        _log("  dir [ruta]              - lista contenido")
        _log("  type <archivo>          - muestra contenido")
        _log("  copy <src> <dst>        - copia archivo/carpeta")
        _log("  move <src> <dst>        - mueve/renombra")
        _log("  ren <src> <dst>         - renombrar (alias rename)")
        _log("  del <path> | erase      - borrar archivo/carpeta")
        _log("  rmdir <dir> | rd        - borrar carpeta (recursivo)")
        _log("  md <dir> | mkdir        - crear carpeta")
        _log("  tree [ruta]             - árbol de directorios")
        _log("  echo <txt>              - imprime texto")
        _log("  echo <txt> >  <archivo> - escribe archivo")
        _log("  echo <txt> >> <archivo> - agrega al archivo")

    @command("cls", "clear")
    def cmd_clear(args):
        # Limpia la consola kernel (simple_console)
        console_log[:] = []

        # Limpia la consola DDLC (console_screen)
        try:
            renpy.store.console_history[:] = []   # <- MUTAR la lista en store
        except Exception:
            pass

        # Restablece estado de UI (evita que reinyecte líneas)
        try:
            renpy.store._console_seen = 0
            renpy.store.new_input = None
        except Exception:
            pass

        # Refresca la interacción actual para que el vaciado se vea inmediato
        try:
            renpy.restart_interaction()
        except Exception:
            pass


    @command("time")
    def cmd_time(args):
        _ok(time.strftime("%Y-%m-%d %H:%M:%S"))

    @command("pwd")
    def cmd_pwd(args):
        rel = renpy.store.console_cwd_rel or ""
        base = "C:/host" if KERNEL_HOST_MODE else "C:/project"
        _ok(_norm_rel(base + (("/" + rel.strip("/")) if rel else "")))

    @command("cd", "chdir")
    def cmd_cd(args):
        if not args:
            return cmd_pwd([])
        target = args[0].strip()
        if target == "\\":
            new_rel = ""
        else:
            abs_target = _abs_from(target, renpy.store.console_cwd_rel)
            if not abs_target: return _err("ruta fuera del root")
            if not os.path.exists(abs_target): return _err("no existe")
            if not os.path.isdir(abs_target): return _err("no es carpeta")
            new_rel = _rel_from_abs(abs_target) if not KERNEL_HOST_MODE else _unixify(os.path.abspath(abs_target))
        renpy.store.console_cwd_rel = new_rel
        return cmd_pwd([])

    @command("dir")
    def cmd_dir(args):
        rel = args[0] if args else ""
        abs_target = _abs_from(rel, renpy.store.console_cwd_rel)
        if not abs_target: return _err("ruta fuera del root")
        if not os.path.exists(abs_target): return _err("no existe")
        if os.path.isfile(abs_target):
            st = os.stat(abs_target)
            _log(" Archivo: {}".format(_norm_rel(os.path.basename(abs_target))))
            _log(" Tamaño:  {}".format(st.st_size))
            _log(" Modif.:  {}".format(_fmt_time(st.st_mtime)))
            return
        _print_dir(abs_target, _rel_from_abs(abs_target))

    @command("type")
    def cmd_type(args):
        if not args: return _err("uso: type <archivo>")
        abs_p = _abs_from(args[0], renpy.store.console_cwd_rel)
        if not abs_p: return _err("ruta fuera del root")
        if not os.path.isfile(abs_p): return _err("no es archivo")
        with io.open(abs_p, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        for line in data.splitlines():
            _log(line)
        _ok("type")

    @command("copy")
    def cmd_copy(args):
        if len(args) < 2: return _err("uso: copy <src> <dst>")
        src = _abs_from(args[0], renpy.store.console_cwd_rel)
        dst = _abs_from(args[1], renpy.store.console_cwd_rel)
        if not src or not dst: return _err("ruta fuera del root")
        if not os.path.exists(src): return _err("origen no existe")
        try:
            if os.path.isdir(src):
                if os.path.exists(dst): return _err("destino ya existe")
                shutil.copytree(src, dst)
            else:
                _ensure_dir(os.path.dirname(dst))
                shutil.copy2(src, dst)
            _ok("copy: {} -> {}".format(args[0], args[1]))
        except Exception as e:
            _err(repr(e))

    @command("move")
    def cmd_move(args):
        if len(args) < 2: return _err("uso: move <src> <dst>")
        src = _abs_from(args[0], renpy.store.console_cwd_rel)
        dst = _abs_from(args[1], renpy.store.console_cwd_rel)
        if not src or not dst: return _err("ruta fuera del root")
        if not os.path.exists(src): return _err("origen no existe")
        try:
            _ensure_dir(os.path.dirname(dst))
            shutil.move(src, dst)
            _ok("move: {} -> {}".format(args[0], args[1]))
        except Exception as e:
            _err(repr(e))

    @command("ren", "rename")
    def cmd_ren(args):
        if len(args) < 2: return _err("uso: ren <src> <dst>")
        src = _abs_from(args[0], renpy.store.console_cwd_rel)
        dst = _abs_from(args[1], renpy.store.console_cwd_rel)
        if not src or not dst: return _err("ruta fuera del root")
        if not os.path.exists(src): return _err("origen no existe")
        try:
            _ensure_dir(os.path.dirname(dst))
            shutil.move(src, dst)
            _ok("ren: {} -> {}".format(args[0], args[1]))
        except Exception as e:
            _err(repr(e))

    @command("del", "erase")
    def cmd_del(args):
        if not args: return _err("uso: del <path>")
        p = _abs_from(args[0], renpy.store.console_cwd_rel)
        if not p: return _err("ruta fuera del root")
        if not os.path.exists(p): return _err("no existe")
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            _ok("del: " + args[0])
        except Exception as e:
            _err(repr(e))

    @command("rmdir", "rd")
    def cmd_rmdir(args):
        if not args: return _err("uso: rmdir <dir>")
        p = _abs_from(args[0], renpy.store.console_cwd_rel)
        if not p: return _err("ruta fuera del root")
        if not os.path.exists(p): return _err("no existe")
        if not os.path.isdir(p): return _err("no es carpeta")
        try:
            shutil.rmtree(p)
            _ok("rmdir: " + args[0])
        except Exception as e:
            _err(repr(e))

    @command("md", "mkdir")
    def cmd_mkdir(args):
        if not args: return _err("uso: mkdir <dir>")
        p = _abs_from(args[0], renpy.store.console_cwd_rel)
        if not p: return _err("ruta fuera del root")
        try:
            _ensure_dir(p)
            _ok("mkdir: " + args[0])
        except Exception as e:
            _err(repr(e))

    @command("tree")
    def cmd_tree(args):
        rel = args[0] if args else ""
        root_abs = _abs_from(rel, renpy.store.console_cwd_rel)
        if not root_abs: return _err("ruta fuera del root")
        if not os.path.exists(root_abs): return _err("no existe")
        _log(_norm_rel("Directorio: " + ("C:/project/" + _rel_from_abs(root_abs))))
        for current, dirs, files in os.walk(root_abs):
            level = len(os.path.relpath(current, root_abs).split(os.sep))
            indent = "│   " * (0 if current == root_abs else max(0, level-1))
            base = os.path.basename(current)
            _log("{}{}".format(indent, base if base else "\\"))
            for d in sorted(dirs):
                _log("{}│   ├── {}".format(indent, d))
            for f in sorted(files):
                _log("{}│   └── {}".format(indent, f))
        _ok("tree")

    @command("echo")
    def cmd_echo(args):
        if not args:
            return _log("")
        # Redirección: > y >> (simple)
        if ">" in args or ">>" in args:
            sym = ">>" if ">>" in args else ">"
            try:
                idx = args.index(sym)
                text = " ".join(args[:idx])
                target = args[idx+1]
                mode = "a" if sym == ">>" else "w"
            except Exception:
                return _err("uso: echo <texto> " + sym + " <archivo>")
            p = _abs_from(target, renpy.store.console_cwd_rel)
            if not p: return _err("ruta fuera del root")
            try:
                _ensure_dir(os.path.dirname(p))
                with io.open(p, mode, encoding="utf-8") as f:
                    try: f.write(unicode(text))
                    except: f.write(text)
                _ok("echo redirigido: " + target)
            except Exception as e:
                _err(repr(e))
        else:
            _log(" ".join(args))

    # ---------- Dispatcher ----------
    def handle_console_command(line):
        s = (line or "").strip()
        if not s: return
        console_receive(_prompt().rstrip(), s)
        parts = s.split()
        name, args = parts[0].lower(), parts[1:]
        fn = COMMANDS.get(name)
        if fn:
            try:
                fn(args)
            except Exception as e:
                _err("excepción: %r" % e)
        else:
            _err("comando desconocido. usa 'help'.")

    # ---------- Abrir/Cerrar ----------
    def console_open_screen():
        renpy.store.console_open = True
        renpy.show_screen("simple_console")

    def console_close_screen():
        renpy.store.console_open = False
        renpy.hide_screen("simple_console")

# ------------------ Hotkeys globales ------------------
screen console_hotkeys():
    key "K_F9" action If(not console_open, Function(console_open_screen))
    key "K_F10" action If(console_open, Function(console_close_screen))

init -2 python:
    if "console_hotkeys" not in config.overlay_screens:
        config.overlay_screens.append("console_hotkeys")
