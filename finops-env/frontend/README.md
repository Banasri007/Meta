# FinOps Cloud Optimizer - Frontend

A modern React-based web interface for the FinOps Cloud Optimization environment.

## Features

- **Real-time Dashboard**: Monitor cloud costs, resources, and system health
- **Task Scoring**: Track progress on 3 difficulty levels (Easy, Medium, Hard)
- **Cost Visualization**: Interactive charts showing cost breakdown by category
- **Resource Management**: View and manage compute, storage, and database resources
- **Quick Actions**: Easy buttons for common optimization tasks
- **Action History**: Track all executed actions and their rewards
- **Responsive Design**: Works on desktop and tablet displays

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure API URL

The frontend looks for the backend API at:
- Default: `https://mahekgupta312006-finops-optimizer.hf.space`
- Or set `REACT_APP_API_URL` environment variable

For local development:
```bash
set REACT_APP_API_URL=http://127.0.0.1:7860
npm start
```

### 3. Start the Frontend

```bash
npm start
```

The app will open at `http://localhost:3000`

## Environment Variables

- `REACT_APP_API_URL`: Backend API URL (default: Hugging Face space)

Example for local backend:
```bash
set REACT_APP_API_URL=http://127.0.0.1:7860
npm start
```

## Dashboard Components

### Metrics Overview
- **Monthly Bill**: Current projected monthly cloud cost
- **System Latency**: Current system latency in milliseconds
- **Throttle Events**: Number of throttling events
- **Downtime Events**: Number of downtime events

### Cost Breakdown
Pie chart showing cost distribution across:
- Compute (EC2, etc.)
- Storage (EBS, etc.)
- Database (RDS, etc.)

### Task Scores
Progress bars for three optimization tasks:
1. **Cleanup Unattached** (Easy): Delete unused volumes and idle instances
2. **Rightsize Compute** (Medium): Downsize underutilized VMs
3. **Fleet Strategy** (Hard): Achieve 40%+ cost reduction with positive ROI

### Cloud Resources
Searchable/scrollable list of all resources showing:
- Resource ID and type
- Monthly cost
- CPU and memory utilization
- Quick action buttons

### Quick Actions
- **Compute Optimizations**: Resize instances to smaller types
- **Resource Cleanup**: Delete unattached volumes
- **Savings Plans**: Purchase 1-year compute/database plans

### Action History
Log of all executed actions with timestamps and rewards

## Development

### Project Structure

```
frontend/
├── src/
│   ├── App.js          # Main component with dashboard
│   ├── index.js        # React entry point
│   └── index.css       # Tailwind styles
├── public/
│   └── index.html      # HTML template
├── package.json        # Dependencies
├── tailwind.config.js  # Tailwind configuration
└── postcss.config.js   # PostCSS configuration
```

### Available Scripts

- `npm start`: Start development server (port 3000)
- `npm build`: Create production build
- `npm test`: Run tests
- `npm eject`: Eject from Create React App (one-way operation)

## Technologies Used

- **React 18**: UI framework
- **Axios**: HTTP client for API calls
- **Recharts**: React charting library for visualization
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **Create React App**: Build tooling

## Styling

The frontend uses Tailwind CSS for styling with dark theme (gray-900 background).

### Color Scheme
- Primary: Blue (#3b82f6)
- Success: Green (#10b981)
- Warning: Yellow (#f59e0b)
- Danger: Red (#ef4444)
- Background: Gray-900 (#0f172a)

## API Integration

The frontend calls the following API endpoints:

- `POST /reset`: Reset environment
- `POST /step`: Execute an action
- `GET /state`: Get current state
- `GET /tasks/{task_id}/score`: Get task score

See [../main.py](../main.py) for full API documentation.

## Known Limitations

- Requires JavaScript enabled
- API CORS must be configured for cross-origin requests
- Large inventory (100+ resources) may impact performance

## Troubleshooting

### Can't connect to backend
- Check if backend API is running
- Set `REACT_APP_API_URL` to correct endpoint
- Check CORS settings on backend

### Charts not rendering
- Check browser console for errors
- Ensure Recharts is properly installed
- Try refreshing the page

### Slow performance
- Can occur with many resources (100+)
- Try filtering or paginating in future versions
- Clear browser cache

## Future Enhancements

- [ ] Resource filtering and search
- [ ] Pagination for large inventories
- [ ] Export reports (PDF/CSV)
- [ ] Custom action templates
- [ ] Comparison mode between scenarios
- [ ] Historical trend charts
- [ ] Recommendations engine
- [ ] Mobile app version
