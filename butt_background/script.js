const canvas = document.getElementById("bgCanvas");
const ctx = canvas.getContext("2d");

let width, height;
const nodes = [];
const numNodes = 50;
const maxDistance = 130;

function resize() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

// Generate random nodes with random radius
for (let i = 0; i < numNodes; i++) {
  nodes.push({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.7,
    vy: (Math.random() - 0.5) * 0.7,
    r: Math.random() * 6 + 6
  });
}

function drawButt(x, y, radius = 8) {
  ctx.save();
  const grad = ctx.createRadialGradient(
    x,
    y - radius * 0.5,
    radius * 0.2,
    x,
    y,
    radius
  );
  grad.addColorStop(0, "#ffe5ec");
  grad.addColorStop(1, "#ff99aa");

  ctx.beginPath();
  ctx.moveTo(x - radius, y);
  ctx.bezierCurveTo(x - radius, y - radius, x, y - radius, x, y);
  ctx.bezierCurveTo(x, y - radius, x + radius, y - radius, x + radius, y);
  ctx.bezierCurveTo(x + radius, y + radius, x - radius, y + radius, x - radius, y);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.strokeStyle = "#e68a93";
  ctx.lineWidth = 0.8;
  ctx.stroke();

  // Middle line
  ctx.beginPath();
  ctx.moveTo(x, y - radius);
  ctx.bezierCurveTo(
    x + radius * 0.15,
    y - radius * 0.2,
    x + radius * 0.15,
    y + radius * 0.2,
    x,
    y + radius
  );
  ctx.strokeStyle = "#e68a93";
  ctx.lineWidth = 0.5;
  ctx.stroke();

  ctx.restore();
}

function animate() {
  ctx.clearRect(0, 0, width, height);

  // Move nodes
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    node.x += node.vx;
    node.y += node.vy;
    if (node.x < 0 || node.x > width) node.vx *= -1;
    if (node.y < 0 || node.y > height) node.vy *= -1;
  }

  // Draw connecting lines
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < maxDistance) {
        ctx.strokeStyle = `rgba(0,0,0,${1 - dist / maxDistance})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
  }

  // Draw butt shapes
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    drawButt(node.x, node.y, node.r);
  }

  requestAnimationFrame(animate);
}

animate();
