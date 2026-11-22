import { useId } from "react";

interface UniFlowLogoProps {
  size?: number;
  className?: string;
}

/**
 * Logo nhận diện UniFlow:
 * Kết hợp chữ U học thuật (Trắng), dòng chảy lộ trình & chữ F động (Đỏ TDTU)
 * và nhịp tiến độ tri thức (Xanh lam sáng) trong khung kiến trúc sắc nét.
 */
export function UniFlowLogo({ size = 32, className }: UniFlowLogoProps) {
  const uid = useId().replace(/:/g, "");
  const redGradId = `uf-red-${uid}`;
  const blueGradId = `uf-blue-${uid}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id={redGradId}
          x1="17"
          y1="29"
          x2="29"
          y2="12"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#d71920" />
          <stop offset="100%" stopColor="#ff4d54" />
        </linearGradient>
        <linearGradient
          id={blueGradId}
          x1="15.5"
          y1="19.5"
          x2="29"
          y2="8"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#e0f2fe" />
        </linearGradient>
      </defs>

      {/* Khung kiến trúc vuông sắc nét */}
      <rect
        x="1"
        y="1"
        width="34"
        height="34"
        fill="#002347"
        stroke="rgba(255,255,255,0.22)"
        strokeWidth="1.2"
      />

      {/* Nét trái chữ U — nền tảng học thuật vững chắc */}
      <path
        d="M7 8H12.4V22.4C12.4 23.7 13.3 24.5 14.6 24.5H17.4L14.9 29H12.8C9.2 29 7 26.6 7 22.8V8Z"
        fill="#FFFFFF"
      />

      {/* Nhánh phải chữ U & dòng chảy hướng lên — sắc Đỏ TDTU */}
      <path
        d="M17.2 29L19.7 24.5H21.4C22.7 24.5 23.6 23.7 23.6 22.4V16.4L29 12.2V22.8C29 26.6 26.8 29 23.2 29H17.2Z"
        fill={`url(#${redGradId})`}
      />

      {/* Cánh dòng chảy trên (Flow crest / nét ngang trên chữ F) */}
      <path
        d="M15.6 13.2L20.8 8H29L23.8 13.2H15.6Z"
        fill={`url(#${blueGradId})`}
      />

      {/* Nhịp kết nối trung tâm (nét giữa chữ F / nút tiên quyết) */}
      <path d="M15.6 19.6L18.8 16.4H21.8V19.6H15.6Z" fill="#7DD3FC" />
    </svg>
  );
}
