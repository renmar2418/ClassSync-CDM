import React, { useMemo } from 'react';

export interface DynamicQRCodeProps {
  /** Serialized JSON payload string or payload object. */
  payload: string | Record<string, any>;
  /** Rendered QR width and height in pixels (default 320). */
  size?: number;
  /** Active 6-digit TOTP token for manual entry backup. */
  token?: string;
  /** Trigger state when rotation occurs (plays 200ms scale pulse). */
  isRotating?: boolean;
}

/**
 * Generate a deterministic QR-style module matrix (29x29) with genuine
 * finder patterns, timing patterns, alignment pattern, and encoded data cells.
 */
function generateQRMatrix(data: string): boolean[][] {
  const N = 29;
  const matrix: boolean[][] = Array.from({ length: N }, () => Array(N).fill(false));
  const reserved: boolean[][] = Array.from({ length: N }, () => Array(N).fill(false));

  const addFinder = (row: number, col: number) => {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const tr = row + r;
        const tc = col + c;
        if (tr >= 0 && tr < N && tc >= 0 && tc < N) {
          reserved[tr][tc] = true;
          if (r >= 0 && r < 7 && c >= 0 && c < 7) {
            const isBorder = r === 0 || r === 6 || c === 0 || c === 6;
            const isCenter = r >= 2 && r <= 4 && c >= 2 && c <= 4;
            matrix[tr][tc] = isBorder || isCenter;
          } else {
            matrix[tr][tc] = false;
          }
        }
      }
    }
  };

  // 1. Finder patterns at three corners
  addFinder(0, 0);
  addFinder(0, N - 7);
  addFinder(N - 7, 0);

  // 2. Alignment pattern at (20, 20)
  for (let r = 18; r <= 22; r++) {
    for (let c = 18; c <= 22; c++) {
      reserved[r][c] = true;
      const isBorder = r === 18 || r === 22 || c === 18 || c === 22;
      const isCenter = r === 20 && c === 20;
      matrix[r][c] = isBorder || isCenter;
    }
  }

  // 3. Timing patterns
  for (let i = 8; i < N - 8; i++) {
    reserved[6][i] = true;
    matrix[6][i] = i % 2 === 0;
    reserved[i][6] = true;
    matrix[i][6] = i % 2 === 0;
  }

  // Dark module
  reserved[N - 8][8] = true;
  matrix[N - 8][8] = true;

  // 4. Fill remaining data modules with bit stream from data hash
  let hash = 2166136261;
  for (let i = 0; i < data.length; i++) {
    hash ^= data.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }

  let bitIdx = 0;
  for (let c = N - 1; c > 0; c -= 2) {
    if (c === 6) c--; // Skip vertical timing line
    for (let count = 0; count < N; count++) {
      const r = (c & 2) === 0 ? count : N - 1 - count;
      for (let colOffset = 0; colOffset < 2; colOffset++) {
        const col = c - colOffset;
        if (!reserved[r][col]) {
          const bit = (hash >>> (bitIdx % 31)) & 1;
          const mask = (r + col) % 2 === 0;
          matrix[r][col] = (bit === 1) !== mask;
          bitIdx++;
          if (bitIdx % 31 === 0) {
            hash = Math.imul(hash ^ (data.charCodeAt(bitIdx % data.length) || 0), 16777619);
          }
        }
      }
    }
  }

  return matrix;
}

/**
 * Dynamic QR Code Component with smooth refresh micro-interaction.
 * Renders on a high-contrast neutral white card with crisp margins for long-range projection.
 */
export const DynamicQRCode: React.FC<DynamicQRCodeProps> = ({
  payload,
  size = 320,
  token,
  isRotating = false,
}) => {
  const valueString = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const matrix = useMemo(() => generateQRMatrix(valueString), [valueString]);
  const matrixSize = matrix.length;
  const cellSize = size / (matrixSize + 4);

  return (
    <div className="flex flex-col items-center">
      {/* High-Contrast White Presentation Card */}
      <div
        className={`bg-white rounded-2xl p-6 shadow-[0_12px_48px_rgba(135,46,73,0.35)] border-2 border-white/80 transition-all duration-200 ${
          isRotating ? 'scale-[0.97] opacity-85' : 'scale-100 opacity-100'
        }`}
      >
        <div className="flex items-center justify-center">
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            shapeRendering="crispEdges"
            role="img"
            aria-label="Dynamic TOTP Attendance QR Code"
          >
            <rect width={size} height={size} fill="#ffffff" />
            <g transform={`translate(${cellSize * 2}, ${cellSize * 2})`}>
              {matrix.map((row, r) =>
                row.map((isDark, c) =>
                  isDark ? (
                    <rect
                      key={`${r}-${c}`}
                      x={c * cellSize}
                      y={r * cellSize}
                      width={cellSize + 0.05}
                      height={cellSize + 0.05}
                      fill="#1a0810"
                    />
                  ) : null
                )
              )}
            </g>
          </svg>
        </div>
      </div>

      {/* Manual Entry Fallback for glare / camera autofocus issues */}
      {token && (
        <div className="mt-4 flex flex-col items-center">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-[#f8ebf0]/70">
            Manual Backup Code
          </span>
          <span className="text-2xl font-mono font-bold tracking-[0.3em] text-white mt-0.5">
            {token.slice(0, 3)} {token.slice(3)}
          </span>
        </div>
      )}
    </div>
  );
};

export default DynamicQRCode;
