import React, { useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import CommentBox from '../shared/CommentBox';

function SortableItem({ item, rank }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="flex items-center gap-4 p-4 bg-slate-900/60 border border-white/5 rounded-xl cursor-grab active:cursor-grabbing"
    >
      <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-fuchsia-500/20 text-fuchsia-100 rounded-full font-semibold text-lg">
        {rank}
      </div>
      {item.image_url && (
        <img
          src={item.image_url}
          alt={item.name}
          className="w-12 h-12 object-contain"
        />
      )}
      <div className="flex-1">
        <h3 className="font-semibold text-white">{item.name}</h3>
        {item.group_name && (
          <p className="text-slate-400 text-sm">{item.group_name}</p>
        )}
      </div>
      <div className="text-slate-500">
        ⋮⋮
      </div>
    </div>
  );
}

function RankedList({ items, onVote, loading }) {
  const [orderedItems, setOrderedItems] = useState(items);
  const [comment, setComment] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      setOrderedItems((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleSubmit = () => {
    const choices = orderedItems.map((item) => item.id);
    onVote(choices, comment);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <p className="text-center text-slate-300 mb-6">
        Drag and drop to rank from best (top) to worst (bottom):
      </p>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={orderedItems.map((i) => i.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-3">
            {orderedItems.map((item, index) => (
              <SortableItem key={item.id} item={item} rank={index + 1} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="text-center mt-8">
        <CommentBox onSubmit={setComment} />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="mt-6 px-8 py-3 bg-fuchsia-600 text-white text-lg font-semibold rounded-full
                     hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        >
          {loading ? 'Submitting...' : 'Submit Rankings'}
        </button>
      </div>
    </div>
  );
}

export default RankedList;
