init -2 python:
    # Garantiza que kernel_exec_capture exista antes de run_input_cmd
    try:
        kernel_exec_capture
    except NameError:
        import os
        def _kernel_available():
            # Deben existir en globals cuando el kernel real esté cargado
            return ("handle_console_command" in globals()) and ("console_receive" in globals())

        def kernel_exec_capture(cmd):
            """
            Captura salida del kernel real si está disponible.
            Si no, devuelve un mensaje claro (pero NO truena).
            """
            if not _kernel_available():
                return u"(kernel no disponible)"
            captured = []
            orig_recv = console_receive

            def tap_recv(sender, line):
                try:
                    # Forzar unicode en Py2
                    try:
                        captured.append(line if isinstance(line, unicode) else unicode(line))
                    except:
                        captured.append(unicode(str(line), errors="ignore"))
                except:
                    captured.append(u"(tap error)")
                try:
                    orig_recv(sender, line)
                except:
                    pass

            try:
                renpy.store.console_receive = tap_recv
                handle_console_command(cmd)
            except Exception as e:
                try:
                    captured.append(u"ERR(exec): %r" % e)
                except:
                    captured.append(u"ERR(exec)")
            finally:
                renpy.store.console_receive = orig_recv

            return u"\n".join(captured).strip()

init 0 python:
    import re, os, stat

    _RE_OS_REMOVE = re.compile(r'^\s*os\.remove\(\s*([\'"])(.+?)\1\s*\)\s*$', re.I)
    ALLOW_LITERAL_MUTATIONS = True

    def _abs_from_basedir(rel_or_abs):
        base = os.path.abspath(config.basedir)
        s = (rel_or_abs or "").strip()
        s_unix = s.replace("\\", "/")
        if os.path.isabs(s_unix):
            abs_p = os.path.abspath(s_unix)
        else:
            if s_unix.startswith("/"):
                s_unix = s_unix.lstrip("/")
            abs_p = os.path.abspath(os.path.join(base, s_unix))
        if not (abs_p == base or abs_p.startswith(base + os.sep)):
            return None
        return abs_p

    def _do_remove_abs(abs_path):
        if not os.path.exists(abs_path):
            return u"ERR: no existe {}".format(abs_path)
        if os.path.isdir(abs_path):
            return u"ERR: es carpeta (usa rmdir) {}".format(abs_path)
        try:
            try:
                mode = os.stat(abs_path).st_mode
                if not (mode & stat.S_IWRITE):
                    os.chmod(abs_path, stat.S_IWRITE)
            except Exception:
                pass
            os.remove(abs_path)
            return u"OK: removed {}".format(abs_path)
        except Exception as e:
            try:
                return u"ERR: {}".format(unicode(repr(e)))
            except:
                return u"ERR: {}".format(repr(e))

    # >>> ESTA es la firma correcta (nota: narrative_output y **kwargs)
    def _literal_os_remove_bridge(cmd, narrative_output=None, **kwargs):
        # Soporta alias legacy: output=
        if narrative_output is None and "output" in kwargs:
            narrative_output = kwargs.get("output")

        m = _RE_OS_REMOVE.match(cmd or "")
        if not m:
            return (False, None)

        target_raw = m.group(2)
        abs_p = _abs_from_basedir(target_raw)
        if not abs_p:
            tech = u"ERR: ruta fuera de config.basedir"
        else:
            tech = _do_remove_abs(abs_p)

        parts = [tech]
        if narrative_output:
            parts.append(narrative_output)
        return (True, u"\n".join(parts))


    # Hookea ANTES del kernel_exec_capture.
    def run_input_cmd(cmd):
        c = (cmd or "").strip()

        # clear/cls fast-path
        if c.lower() in ("clear", "cls"):
            try:
                renpy.store.console_history[:] = []
                renpy.store._console_seen = 0
                renpy.store.new_input = None
            except Exception:
                pass
            renpy.restart_interaction()
            return

        # --- HOOK LITERAL TAMBIÉN AQUÍ ---
        # Literal os.remove con narrativa
        handled, out = _literal_os_remove_bridge(c)
        if handled:
            run_input(input="> " + c, output=out or u"(sin salida)")
            return
        # --- FIN HOOK ---

        # Flujo normal
        out = kernel_exec_capture(c)
        if not out:
            out = u"(sin salida)"
        run_input(input="> " + c, output=out)

    def console_submit(cmd):
        c = (cmd or "").strip()
        if not c:
            return
        # Ejecutar en nuevo contexto (no bloquea UI)
        renpy.invoke_in_new_context(run_input_cmd, c)
