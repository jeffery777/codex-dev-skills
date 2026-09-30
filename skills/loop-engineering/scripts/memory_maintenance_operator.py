"""正式 operator CLI 的逐次接受介面；同 OS 帳號屬明示接受的 TCB。

TTY 身分不能證明人類；agent 模式須先取得使用者對操作範圍的明確委派。
Actor 標籤只記錄操作者種類，不建立委派權限。沒有 callback、stdin、yes flag 或
保存 confirmation 接口。所有接受僅存在當次程序，期限及撤銷仍由 core/host 核對。
"""
from __future__ import annotations

import os
import stat
import termios
import uuid

import memory_governance_contract as c
from memory_governance_host import AcceptedPreview


def display_safe(data):
    """Canonical JSON 會 escape ASCII controls；另拒絕能偽裝顯示順序的 controls。"""
    text = data.decode('utf-8')
    c.require(not any(ch in text for ch in '\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'),
              'unsafe-display')
    c.require(all(ord(ch) >= 32 or ch in '\n\r\t' for ch in text)
              and not any(127 <= ord(ch) <= 159 for ch in text), 'unsafe-display')
    return data


class OperatorTerminal:
    """Human 或已受委派的 agent 控制當次 terminal；非抗惡意 same-UID 認證。"""

    def __init__(self, *, actor='human'):
        self.actor = c.one_of(actor, {'human', 'agent'}, 'scope-unavailable')
        self.fd = None
        self.pid = os.getpid()
        self.evidence_id = self.actor + '-operator-' + uuid.uuid4().hex

    def __enter__(self):
        c.require(os.isatty(0), 'operator-terminal-unavailable')
        fd = os.open('/dev/tty', os.O_RDWR | os.O_NOCTTY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            c.require(stat.S_ISCHR(info.st_mode) and os.isatty(fd)
                      and os.tcgetpgrp(fd) == os.getpgrp(), 'operator-terminal-unavailable')
            flags = termios.tcgetattr(fd)
            c.require(flags[3] & termios.ICANON and flags[3] & termios.ECHO,
                      'operator-terminal-unavailable')
            self.fd = fd
            return self
        except BaseException:
            os.close(fd)
            raise

    def __exit__(self, *_args):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def check(self):
        c.require(self.fd is not None and os.getpid() == self.pid
                  and os.tcgetpgrp(self.fd) == os.getpgrp(), 'operator-terminal-unavailable')

    def write(self, data):
        self.check()
        display_safe(data)
        offset = 0
        while offset < len(data):
            written = os.write(self.fd, data[offset:])
            c.require(written > 0, 'output-unavailable')
            offset += written

    def accept(self, action, data):
        """先完整顯示再清除預先排隊輸入；接受只對本次完整 bytes 有效。"""
        self.check()
        c.opaque(action)
        c.require(type(data) is bytes and len(data) <= c.MAX_ENVELOPE, 'input-too-large')
        value = c.decode(data)
        c.require(c.canonical(value) == data, 'noncanonical-preview')
        display_safe(data)
        token = action + ' ' + c.digest(value)
        self.write(data + b'\n')
        reviewer = '已取得使用者委派的 agent' if self.actor == 'agent' else '人類操作者'
        self.write(('請由' + reviewer + '審查上述完整內容；接受請輸入 ' + token + '\n> ').encode())
        termios.tcflush(self.fd, termios.TCIFLUSH)
        answer = bytearray()
        while len(answer) <= 160:
            chunk = os.read(self.fd, 1)
            if not chunk:
                return False
            answer.extend(chunk)
            if chunk == b'\n':
                self.check()
                return bytes(answer) == (token + '\n').encode('ascii')
        return False

    def accept_preview(self, binding, data, clock):
        preview = c.decode(data)
        c.require(preview['scope'] == c.decode(binding.scope_bytes), 'root-binding-mismatch')
        c.require(self.accept(preview['operation'].upper(), data), 'request-not-accepted')
        # Host/core independently recheck both clocks, sources, state and revocation.
        return AcceptedPreview(data, c.canonical({
            'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
            'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': clock.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': self.evidence_id,
        }))
