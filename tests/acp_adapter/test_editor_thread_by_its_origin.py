"""A conversation the owner stores as ``local`` stays listable and reopenable (#143547).

The gateway owner relabels every editor thread: ``source='local'``, with the ACP origin kept only in
``created_source`` (and in the session's policy receipt). The label alone therefore proves nothing about
where a conversation came from, and the row carries its working directory in the ``cwd`` column, not in
``model_config``. Both halves are what this file pins: the manager's own listing and its reopen path.
"""
from types import SimpleNamespace

from acp_adapter.session import SessionManager
from hermes_state import SessionDB


def _editor_thread(db, sid, cwd):
    """A row as the owner leaves it after adopting an editor conversation."""
    db.create_session(session_id=sid, source='local', cwd=str(cwd))
    db._execute_write(lambda conn, sid=sid: conn.execute(
        'UPDATE sessions SET created_source = ? WHERE id = ?', ('acp', sid)))
    db.append_message(sid, 'user', 'a saved turn')


def test_the_managers_listing_keeps_an_editor_thread_by_its_origin(tmp_path):
    with SessionDB(tmp_path / 'state.db') as db:
        _editor_thread(db, 'editor-thread', tmp_path)
        db.create_session(session_id='cli-chat', source='local', cwd=str(tmp_path))
        db.append_message('cli-chat', 'user', 'a saved turn')
        manager = SessionManager(db=db, agent_factory=lambda: SimpleNamespace(model='fixture'))
        listed = [row['session_id'] for row in manager.list_sessions(cwd=str(tmp_path))]
    assert listed == ['editor-thread']


def test_an_editor_thread_reopens_with_the_cwd_of_its_row(tmp_path):
    with SessionDB(tmp_path / 'state.db') as db:
        _editor_thread(db, 'editor-thread', tmp_path)
        manager = SessionManager(db=db, agent_factory=lambda: SimpleNamespace(model='fixture'))
        state = manager.get_session('editor-thread')
    assert state is not None
    assert state.cwd == str(tmp_path)
