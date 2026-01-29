export default function Input({
  value,
  onChange,
  placeholder,
  type = "text",
  className = "",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full rounded-xl bg-slate-100 px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:bg-white focus:shadow-soft ${className}`}
    />
  );
}
