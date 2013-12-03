# -*- coding:utf-8 -*-
import util
import tmux_cmd
import tmux_obj
import config
import datetime,time
import os,sys
from os import path 


LOG = util.get_logger()

WIN_BASE_IDX = int(tmux_cmd.get_option('base-index'))
#PANE_BASE_IDX = tmux_cmd.get_option('pane-base-index')

def restore_tmux(tmux_id):
    """
    retore tmux sessions by given backuped Tmux id
    0 - read all backups from $HOME/.tmuxback/backup
    1 - if the given tmux_id is empty, take the latest
    2 - throw error msg if given name doesn't exist
    3 - check if there is tmux running and with same session name
    4 - handle windows, panes ..
    """
    #validate given tmux_id
    tmux_id = chk_tmux_id(tmux_id)

    LOG.info('loading backuped tmux sessions')
    jsonfile = os.path.join(config.BACKUP_PATH,tmux_id,tmux_id+'.json')
    LOG.debug('load json file:%s'% jsonfile )

    tmux = util.json_to_obj(jsonfile)
    LOG.debug('converted json file to Tmux object')
    LOG.info('backuped tmux sessions loaded')
    
    for sess in  tmux.sessions:
        LOG.debug('processing session name %s'%sess.name)
        #check if session exists
        if tmux_cmd.has_session(sess.name):
            LOG.info('found session with same name in current tmux, \
skip restoring the session:%s.' % sess.name)
            continue
        restore_session(sess, tmux_id)


def restore_session(sess, tmux_id):
    """create the session from session object"""
    LOG.debug('create session, with initial win: %s' % sess.name)
    tmux_cmd.create_session(sess.name,sess.size)
    for win in sess.windows_in_reverse()[:-1]:
        #rename, renumber window
        restore_window(win, tmux_id)

        LOG.debug('create empty window with baseIdx: %s' % WIN_BASE_IDX)
        tmux_cmd.create_empty_window(sess.name, WIN_BASE_IDX)

    # the last window
    restore_window(sess.windows_in_reverse()[-1], tmux_id)


def restore_window(win, tmux_id):
    LOG.info('restoring window: %s' % win.sess_name+':'+str(win.win_id))
    #renumber from base_index to backuped index
    if WIN_BASE_IDX != win.win_id:
        tmux_cmd.renumber_window(win.sess_name, WIN_BASE_IDX, win.win_id)
    #rename win
    tmux_cmd.rename_window(win.sess_name,win.win_id,win.name)
    
    #select window (active)
    if win.active:
        tmux_cmd.active_window(win.sess_name,win.win_id)

    if len(win.panes) >1 :
        #multiple panes
        #split
        for i in range(len(win.panes)-1):
            tmux_cmd.split_window(win.sess_name,win.win_id,win.min_pane_id())

    for p in win.panes:
        restore_pane(p, tmux_id)

    #set layout
    tmux_cmd.select_layout(win.sess_name, win.win_id, win.layout)

def restore_pane(pane, tmux_id):
    LOG.info('restoring pane: %s'% pane.idstr())
    #set path
    tmux_cmd.set_pane_path(pane.idstr(), pane.path)

    #restore content
    filename = os.path.join(config.BACKUP_PATH,tmux_id,pane.idstr())

    tmux_cmd.restore_pane_content(pane.idstr(), filename)


def chk_tmux_id(tmux_id):
    """check the tmux_id (backup name)"""
    #if no backup exists, exit application
    all_bk =util.all_backups() 
    if len(all_bk)<1:
        LOG.error('backup dir is empty, nothing to restore')
        sys.exit(1)

    #checking tmux_id
    if tmux_id:
        if not all_bk.__contains__(tmux_id):
            LOG.error('cannot find given backup name')
            sys.exit(1)
    else:
        tmux_id = util.latest_backup().split('/')[-1]
        LOG.info('backup name is empty, using last backup:%s'%tmux_id)

    return tmux_id

