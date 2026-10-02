import { useId, useState, type ReactNode } from "react";

/** 两步的按钮：先点按钮，展开一个输入框，再点一次提交（拒绝、完成、取消认领、已解决都用它）。 */
export function TextAction(props: {
  label: string;
  submitLabel?: string;
  field: string;
  hint?: ReactNode;
  required?: boolean;
  disabled?: boolean;
  busy?: boolean;
  primary?: boolean;
  maxLength?: number;
  extra?: (open: boolean) => ReactNode;
  onSubmit: (text: string) => Promise<boolean>;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [tried, setTried] = useState(false);
  const id = useId();
  const empty = !text.trim();
  const missing = props.required && empty;

  if (!open) {
    return (
      <button
        type="button"
        className={props.primary ? "btn btn-primary" : "btn"}
        disabled={props.disabled || props.busy}
        onClick={() => setOpen(true)}
      >
        {props.label}
      </button>
    );
  }
  const submit = async () => {
    setTried(true);
    if (missing) return;
    if (await props.onSubmit(text.trim())) {
      setOpen(false);
      setText("");
      setTried(false);
    }
  };
  return (
    <div className="inline-form">
      <label htmlFor={id} className="field-label">
        {props.field}
      </label>
      {props.hint && <p className="hint">{props.hint}</p>}
      <textarea
        id={id}
        rows={3}
        value={text}
        maxLength={props.maxLength ?? 2000}
        onChange={(e) => setText(e.target.value)}
        aria-invalid={tried && missing ? true : undefined}
      />
      {tried && missing && <p className="field-error">请先写一句再提交。</p>}
      {props.extra?.(open)}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={props.disabled || props.busy} onClick={() => void submit()}>
          {props.submitLabel ?? props.label}
        </button>
        <button
          type="button"
          className="btn"
          disabled={props.busy}
          onClick={() => {
            setOpen(false);
            setTried(false);
          }}
        >
          收起
        </button>
      </div>
    </div>
  );
}

/** 评论框。 */
export function CommentBox({ busy, onSubmit }: { busy: boolean; onSubmit: (text: string) => Promise<boolean> }) {
  const [text, setText] = useState("");
  const id = useId();
  const left = 2000 - text.length;
  return (
    <form
      className="comment-box"
      onSubmit={(e) => {
        e.preventDefault();
        if (!text.trim()) return;
        void onSubmit(text.trim()).then((ok) => ok && setText(""));
      }}
    >
      <label htmlFor={id} className="field-label">
        评论
      </label>
      <textarea id={id} rows={3} value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} placeholder="想说什么，写在这里" />
      {left < 200 && <p className="hint">还能写 {left} 字。</p>}
      <div className="btn-row">
        <button type="submit" className="btn" disabled={busy || !text.trim()}>
          评论
        </button>
      </div>
      <p className="hint">您写的评论，别人的 agent 要等那个人接受正文或转发之后才读得到。</p>
    </form>
  );
}
