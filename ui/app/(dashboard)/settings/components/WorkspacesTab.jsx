
'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit2, Check, X, Loader2, Layout, ArrowRightLeft, Trash2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { fetchWorkspaces, createWorkspace, renameWorkspace, switchWorkspace, deleteWorkspace } from '@/lib/api';

export default function WorkspacesTab({ user }) {
    const [workspaces, setWorkspaces] = useState([]);
    const [loading, setLoading] = useState(true);
    const [createName, setCreateName] = useState('');
    const [creating, setCreating] = useState(false);
    const [renamingId, setRenamingId] = useState(null);
    const [renameValue, setRenameValue] = useState('');
    const [switchingId, setSwitchingId] = useState(null);
    const [deleteConfirmId, setDeleteConfirmId] = useState(null);
    const [deletingId, setDeletingId] = useState(null);

    useEffect(() => {
        loadWorkspaces();
    }, []);

    const loadWorkspaces = async () => {
        try {
            const data = await fetchWorkspaces();
            setWorkspaces(data.workspaces || []);
        } catch (err) {
            console.error('Failed to load workspaces:', err);
            toast.error('Failed to load workspaces');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!createName.trim()) return;

        setCreating(true);
        try {
            const newWs = await createWorkspace({ name: createName });
            setWorkspaces([...workspaces, newWs]);
            setCreateName('');
            toast.success('Workspace created');

            // Optional: Switch to new workspace immediately?
            // For now, just let them see it in the list.
        } catch (err) {
            console.error('Failed to create workspace:', err);
            toast.error('Failed to create workspace');
        } finally {
            setCreating(false);
        }
    };

    const handleRename = async (id) => {
        if (!renameValue.trim()) return;

        try {
            const updated = await renameWorkspace({ workspaceId: id, name: renameValue });
            setWorkspaces(workspaces.map(ws => ws.id === id ? { ...ws, name: updated.name } : ws));
            setRenamingId(null);
            setRenameValue('');
            toast.success('Workspace renamed');

            // If renaming current workspace, might need to reload to update context/sidebar
            if (user?.workspace_id === id) {
                window.location.reload();
            }
        } catch (err) {
            console.error('Failed to rename workspace:', err);
            toast.error('Failed to rename workspace');
        }
    };

    const handleSwitch = async (id) => {
        if (id === user?.workspace_id) return;

        setSwitchingId(id);
        try {
            await switchWorkspace(id);
            window.location.reload();
        } catch (err) {
            console.error('Failed to switch workspace:', err);
            toast.error('Failed to switch workspace');
            setSwitchingId(null);
        }
    };

    const handleDelete = async (id) => {
        setDeletingId(id);
        try {
            await deleteWorkspace(id);
            toast.success('Workspace deleted');

            // If deleted active workspace, reload to let backend/frontend sync up
            if (user?.workspace_id === id) {
                window.location.reload();
            } else {
                setWorkspaces(workspaces.filter(ws => ws.id !== id));
            }
        } catch (err) {
            console.error('Failed to delete workspace:', err);
            toast.error(err.message || 'Failed to delete workspace');
        } finally {
            setDeletingId(null);
            setDeleteConfirmId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Create Workspace */}
            <div className="bg-white p-6 rounded-xl border border-neutral-200 shadow-sm">
                <h2 className="text-lg font-semibold text-neutral-900 mb-4">Create Workspace</h2>
                <form onSubmit={handleCreate} className="flex gap-4">
                    <div className="flex-1">
                        <input
                            type="text"
                            value={createName}
                            onChange={(e) => setCreateName(e.target.value)}
                            placeholder="Workspace Name"
                            className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={creating || !createName.trim()}
                        className="px-6 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        Create
                    </button>
                </form>
            </div>

            {/* Workspace List */}
            <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-neutral-200">
                    <h2 className="text-lg font-semibold text-neutral-900">Your Workspaces</h2>
                </div>
                <div className="divide-y divide-neutral-100">
                    {workspaces.map((ws) => (
                        <div key={ws.id} className="p-4 flex items-center justify-between hover:bg-neutral-50 transition-colors">
                            <div className="flex items-center gap-4 flex-1">


                                {renamingId === ws.id ? (
                                    <div className="flex items-center gap-2 flex-1 max-w-md">
                                        <input
                                            type="text"
                                            value={renameValue}
                                            onChange={(e) => setRenameValue(e.target.value)}
                                            className="flex-1 px-3 py-1 text-sm border border-neutral-300 rounded-md focus:ring-2 focus:ring-neutral-900 outline-none"
                                            autoFocus
                                        />
                                        <button
                                            onClick={() => handleRename(ws.id)}
                                            className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                                        >
                                            <Check className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => { setRenamingId(null); setRenameValue(''); }}
                                            className="p-1 text-red-600 hover:bg-red-50 rounded"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                ) : (
                                    <div className="flex flex-col">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium text-neutral-900">{ws.name}</span>
                                            {ws.id === user?.workspace_id && (
                                                <span className="px-2 py-0.5 bg-cyan-100 text-cyan-700 text-xs rounded-full font-medium">
                                                    Active
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-xs text-neutral-500">
                                            Role: {ws.role}
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center gap-2">
                                {renamingId !== ws.id && (
                                    <button
                                        onClick={() => { setRenamingId(ws.id); setRenameValue(ws.name); }}
                                        className="p-2 text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
                                        title="Rename"
                                    >
                                        <Edit2 className="w-4 h-4" />
                                    </button>
                                )}

                                {ws.id !== user?.workspace_id && (
                                    <button
                                        onClick={() => handleSwitch(ws.id)}
                                        disabled={switchingId === ws.id}
                                        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        {switchingId === ws.id ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <ArrowRightLeft className="w-4 h-4" />
                                        )}
                                        Switch
                                    </button>
                                )}

                                {ws.role === 'Owner' && (
                                    deleteConfirmId === ws.id ? (
                                        <div className="flex items-center gap-2 ml-2">
                                            <button
                                                onClick={() => handleDelete(ws.id)}
                                                disabled={deletingId === ws.id}
                                                className="px-3 py-1.5 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                {deletingId === ws.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                                                Confirm
                                            </button>
                                            <button
                                                onClick={() => setDeleteConfirmId(null)}
                                                disabled={deletingId === ws.id}
                                                className="px-3 py-1.5 text-sm font-medium border border-neutral-300 text-neutral-600 rounded-lg hover:bg-neutral-50 transition-colors"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => setDeleteConfirmId(ws.id)}
                                            className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-2"
                                            title="Delete Workspace"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    )
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
