from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from werkzeug.utils import secure_filename
from sqlalchemy import select
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    niche = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_flagged = db.Column(db.Boolean, default=False)  # Add this line if it doesn't exist

    def __repr__(self):
        return f'<User {self.email}>'

    def is_profile_flagged(self):
        return self.is_flagged  # Method to check if the profile is flagged

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    goal = db.Column(db.String(300), nullable=False)
    visibility = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Active')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flag_reason = db.Column(db.String(500))
    flag_date = db.Column(db.DateTime)

    user = db.relationship('User', backref=db.backref('campaigns', lazy=True))

    def __repr__(self):
        return f'<Campaign {self.name}>'

class Influencer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image = db.Column(db.String(300), nullable=True)
    niche = db.Column(db.String(100), nullable=False)
    reach = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref=db.backref('influencer', uselist=False))

    def __repr__(self):
        return f'<Influencer {self.user_id}>'

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('influencer.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_task = db.Column(db.String(300), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    payment_amount = db.Column(db.Float, nullable=True)
    campaign_name = db.Column(db.String(150), nullable=False)  # Added campaign_name field
    negotiation = db.Column(db.Float, nullable=True)  # Added negotiation field

    sponsor = db.relationship('User', foreign_keys=[sponsor_id], backref=db.backref('sent_requests', lazy=True))
    influencer = db.relationship('User', foreign_keys=[influencer_id], backref=db.backref('received_requests', lazy=True))

    def __repr__(self):
        return f'<Request {self.id}>'

class Requesttt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_task = db.Column(db.String(300), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    payment_amount = db.Column(db.Float, nullable=True)
    campaign_name = db.Column(db.String(150), nullable=False)  # Added campaign_name field
    negotiation = db.Column(db.Float, nullable=True)  # Added negotiation field

    sponsor = db.relationship('User', foreign_keys=[sponsor_id], backref=db.backref('sent_requesttts', lazy=True))
    influencer = db.relationship('User', foreign_keys=[influencer_id], backref=db.backref('received_requesttts', lazy=True))

    def __repr__(self):
        return f'<Requesttt {self.id}>'



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    name = request.form.get('name')
    email = request.form.get('email')
    user_type = request.form.get('user_type')
    niche = request.form.get('niche')
    password = request.form.get('password')

    new_user = User(name=name, email=email, user_type=user_type, niche=niche, password=password)

    try:
        db.session.add(new_user)
        db.session.commit()

        if user_type == 'influencer':
            new_influencer = Influencer(user_id=new_user.id, niche=niche, reach=0, rating=0.0)
            db.session.add(new_influencer)
            db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        flash('Email address already exists. Please use a different email.', 'error')
        return redirect(url_for('signup'))

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    user_type = request.form.get('user_type')

    if email == 'admin@gmail.com' and password == 'admin@123':
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(
                name='Admin User',
                email=email,
                user_type='admin',
                niche='admin',
                password='admin@123'
            )
            db.session.add(user)
            db.session.commit()
        login_user(user)
        flash('Login successful!', 'success')
        return redirect(url_for('admindash'))

    user = User.query.filter_by(email=email, user_type=user_type).first()

    if not user or user.password != password:
        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('login'))

    if user.is_flagged:  # Check if the user is flagged
        flash('Your account has been flagged and cannot be accessed. Please contact support.', 'error')
        return redirect(url_for('login'))

    login_user(user)
    flash('Login successful!', 'success')

    if user.user_type == 'influencer':
        return redirect(url_for('influencerdash'))
    elif user.user_type == 'sponsor':
        return redirect(url_for('sponsordash'))
    elif user.user_type == 'admin':
        return redirect(url_for('admindash'))


@app.route('/admindash')
@login_required
def admindash():
    if current_user.user_type != 'admin':
        flash('Access denied. You must be an admin to view this page.', 'error')
        return redirect(url_for('index'))

    # Fetch ongoing campaigns (not flagged)
    ongoing_stmt = select(Campaign.id, Campaign.name, Campaign.visibility, Campaign.budget, User.name.label('sponsor_name'))\
        .join(User)\
        .where(Campaign.status != 'Flagged')
    ongoing_campaigns = db.session.execute(ongoing_stmt).all()

    # Fetch flagged campaigns
    flagged_stmt = select(Campaign.id, Campaign.name, Campaign.flag_reason, Campaign.flag_date, User.name.label('sponsor_name'))\
        .join(User)\
        .where(Campaign.status == 'Flagged')
    flagged_campaigns = db.session.execute(flagged_stmt).all()

    return render_template('admindash.html', current_user=current_user, ongoing_campaigns=ongoing_campaigns, flagged_campaigns=flagged_campaigns)
@app.route('/flag_campaign', methods=['POST'])
@login_required
def flag_campaign():
    if current_user.user_type != 'admin':
        flash('Access denied. You must be an admin to flag campaigns.', 'error')
        return redirect(url_for('index'))

    campaign_id = request.form.get('campaign_id')
    campaign = Campaign.query.get(campaign_id)
    
    if campaign:
        campaign.status = 'Flagged'
        campaign.flag_date = datetime.utcnow()
        campaign.flag_reason = "Flagged by admin"  # You can add a reason input if needed
        db.session.commit()
        flash('Campaign has been flagged successfully.', 'success')
    else:
        flash('Campaign not found.', 'error')

    return redirect(url_for('admindash'))

@app.route('/unflag_campaign/<int:campaign_id>', methods=['POST'])
def unflag_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if campaign:
        if campaign.status == 'Flagged':  # Check if the campaign is currently flagged
            campaign.status = 'Active'  # Change status to Active
            db.session.commit()
            flash('Campaign has been unflagged successfully.', 'success')
        else:
            flash('Campaign is not flagged.', 'info')  # Inform that it's not flagged
    else:
        flash('Campaign not found.', 'error')
    return redirect(url_for('admindash'))  # Redirect back to the admin dashboard

@app.route('/adminsearch', methods=['GET', 'POST'])
def adminsearch():
    if request.method == 'POST':
        user_type = request.form.get('type')
        query = request.form.get('query')
        
        # Implement your search logic here
        if user_type and query:
            # Exclude admins from the results
            results = User.query.filter(User.user_type == user_type, User.name.contains(query), User.user_type != 'admin').all()
        else:
            # Default to all users except admins if no search criteria
            results = User.query.filter(User.user_type != 'admin').all()

    else:
        # Default to all users except admins on GET request
        results = User.query.filter(User.user_type != 'admin').all()

    return render_template('adminsearch.html', results=results)

@app.route('/flag_profile/<int:user_id>', methods=['POST'])
def flag_profile(user_id):
    # Logic to flag the profile
    profile = User.query.get(user_id)
    if profile:
        if not profile.is_flagged:  # Check if the profile is already flagged
            profile.is_flagged = True  # Flag the profile
            db.session.commit()
            flash('Profile has been flagged successfully.', 'success')
        else:
            flash('Profile is already flagged.', 'info')  # Inform that it's already flagged
    else:
        flash('Profile not found.', 'error')
    return redirect(url_for('adminsearch'))  # Redirect back to the admin search page


@app.route('/unflag_profile/<int:user_id>', methods=['POST'])
def unflag_profile(user_id):
    profile = User.query.get(user_id)
    if profile:
        if profile.is_flagged:  # Check if the profile is currently flagged
            profile.is_flagged = False  # Unflag the profile
            db.session.commit()
            flash('Profile has been unflagged successfully.', 'success')
        else:
            flash('Profile is not flagged.', 'info')  # Inform that it's not flagged
    else:
        flash('Profile not found.', 'error')
    return redirect(url_for('adminsearch'))  # Redirect back to the admin search page


@app.route('/adminstats')
@login_required
def adminstats():
    total_users = User.query.count()
    total_influencers = User.query.filter_by(user_type='influencer').count()
    total_sponsors = User.query.filter_by(user_type='sponsor').count()
    total_campaigns = Campaign.query.count()
    
    # Count ad requests by status
    total_accepted_requests = Request.query.filter_by(status='Accepted').count() + Requesttt.query.filter_by(status='Accepted').count()
    total_pending_requests = Request.query.filter_by(status='Pending').count() + Requesttt.query.filter_by(status='Pending').count()
    total_rejected_requests = Request.query.filter_by(status='Rejected').count() + Requesttt.query.filter_by(status='Rejected').count()

    # Fetch influencer data by niche
    influencer_data = db.session.query(Influencer.niche, db.func.count(Influencer.id)).group_by(Influencer.niche).all()
    influencer_counts = {niche: count for niche, count in influencer_data}

    # Fetch sponsor data by niche
    sponsor_data = db.session.query(User.niche, db.func.count(User.id)).filter(User.user_type == 'sponsor').group_by(User.niche).all()
    sponsor_counts = {niche: count for niche, count in sponsor_data}

    # Fetch campaign data (public vs private)
    campaign_data = db.session.query(Campaign.visibility, db.func.count(Campaign.id)).group_by(Campaign.visibility).all()
    campaign_counts = {visibility: count for visibility, count in campaign_data}

    # Generate the charts
    generate_chart(total_users, total_influencers, total_sponsors, total_campaigns, total_accepted_requests, total_pending_requests, total_rejected_requests)
    generate_niche_chart(influencer_counts, 'Influencers by Niche')  # Existing function for influencers
    generate_niche_chart(sponsor_counts, 'Sponsors by Niche')  # New function for sponsors
    generate_pie_chart(campaign_counts)  # Pie chart for campaigns
    generate_ad_requests_pie_chart(total_accepted_requests, total_pending_requests, total_rejected_requests)  # New function for ad requests

    return render_template('adminstats.html', total_users=total_users,
                           total_influencers=total_influencers,
                           total_sponsors=total_sponsors,
                           total_campaigns=total_campaigns,
                           total_accepted_requests=total_accepted_requests,
                           total_pending_requests=total_pending_requests,
                           total_rejected_requests=total_rejected_requests)

def generate_chart(total_users, total_influencers, total_sponsors, total_campaigns, total_accepted_requests, total_pending_requests, total_rejected_requests):
    try:
        categories = ['Users', 'Influencers', 'Sponsors', 'Campaigns', 'Accepted Requests', 'Pending Requests', 'Rejected Requests']
        values = [total_users, total_influencers, total_sponsors, total_campaigns, total_accepted_requests, total_pending_requests, total_rejected_requests]

        plt.figure(figsize=(10, 6))
        plt.bar(categories, values, color=['blue', 'orange', 'green', 'red', 'purple', 'cyan', 'gray'])
        plt.xlabel('Categories')
        plt.ylabel('Counts', fontsize=24)
        plt.title('Total Number of', fontsize=24)
        plt.xticks(rotation=18)
        plt.xticks(fontsize=11)  # Increase x-tick font size
        plt.yticks(fontsize=24)  # Increase y-tick font size

        # Set y-axis ticks to increase by 1
        max_value = max(values)  # Get the maximum value for the y-axis limit
        plt.yticks(range(0, max_value + 2, 1))  # Set ticks from 0 to max_value + 1 with a step of 1

        # Save the figure
        chart_path = os.path.join('static', 'chart.png')  # Save in the static folder
        plt.savefig(chart_path)
        plt.close()
    except Exception as e:
        print(f"Error generating chart: {e}")

def generate_niche_chart(niche_data, title):
    print("Generating niche chart with data:", niche_data)  # Debugging line
    niches = list(niche_data.keys())
    counts = list(niche_data.values())

    plt.figure(figsize=(12, 8))  # Adjust size as needed
    plt.bar(niches, counts, color='skyblue')

    # Set font sizes
    plt.xlabel('Niche', fontsize=40)  # Increase x-label font size
    plt.ylabel('Number of Sponsors', fontsize=40)  # Increase y-label font size
    plt.title(title, fontsize=40)  # Use the title parameter
    plt.xticks(fontsize=23)  # Increase x-tick font size
    plt.yticks(fontsize=23)  # Increase y-tick font size

    # Save the figure
    chart_path = os.path.join('static', f'{title.replace(" ", "_").lower()}_chart.png')  # Save in the static folder
    plt.savefig(chart_path)
    plt.close()

def generate_pie_chart(campaign_data):
    labels = list(campaign_data.keys())
    sizes = list(campaign_data.values())

    plt.figure(figsize=(8, 8))  # Adjust size as needed
    wedges, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
    
    # Set font sizes
    plt.setp(texts, fontsize=25)  # Increase label font size
    plt.setp(autotexts, fontsize=25)  # Increase percentage font size
    plt.title('Campaigns by visibility', fontsize=30)  # Increase title font size
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Add legend

    # Save the figure
    chart_path = os.path.join('static', 'campaigns_pie_chart.png')  # Save in the static folder
    plt.savefig(chart_path)
    plt.close()

def generate_ad_requests_pie_chart(accepted_count, pending_count, rejected_count):
    labels = ['Accepted', 'Pending', 'Rejected']
    sizes = [accepted_count, pending_count, rejected_count]

    plt.figure(figsize=(8, 8))  # Adjust size as needed
    wedges, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#66b3ff', '#ff9999', '#ffcc00'])
    
    # Set font sizes
    plt.setp(texts, fontsize=25, rotation=90)  # Increase label font size
    plt.setp(autotexts, fontsize=25)  # Increase percentage font size
    plt.title('Ad Requests by Status', fontsize=30)  # Increase title font size
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Add legend

    # Save the figure
    chart_path = os.path.join('static', 'ad_requests_pie_chart.png')  # Save in the static folder
    plt.savefig(chart_path)
    plt.close()

@app.route('/influencerdash')
@login_required
def influencerdash():
    if current_user.user_type != 'influencer':
        flash('Access denied. You must be an influencer to view this page.', 'error')
        return redirect(url_for('index'))

    # Fetch pending requests (from sponsors to this influencer)
    pending_requests = Request.query.filter_by(influencer_id=current_user.id, status='Pending').all()

    # Fetch sent requests (from this influencer to sponsors)
    sent_requests = Requesttt.query.filter_by(influencer_id=current_user.id).all()

    accepted_requests = Request.query.filter_by(influencer_id=current_user.id, status='Accepted').all()

    return render_template('influencerdash.html', 
                           current_user=current_user, 
                           pending_requests=pending_requests, 
                           sent_requests=sent_requests, accepted_requests=accepted_requests)

@app.route('/influsearch', methods=['GET', 'POST'])
@login_required
def influsearch():
    if request.method == 'POST':
        search_type = request.form['type']
        query = request.form['query']
        if search_type == 'influencer':
            results = User.query.filter(User.user_type == 'influencer', User.name.contains(query)).all()
        else:
            results = User.query.filter(User.user_type == 'sponsor', User.name.contains(query)).all()
    else:
        results = User.query.filter(User.user_type != 'admin').all()
        search_type = ''
        query = ''
    return render_template('influsearch.html', results=results, query=query, search_type=search_type)

@app.route('/influstats')
@login_required
def influstats():
    if current_user.user_type != 'influencer':
        flash('Access denied. You must be an influencer to view this page.', 'error')
        return redirect(url_for('index'))

    # Fetch pending requests (from sponsors to this influencer)
    pending_requests = Request.query.filter_by(influencer_id=current_user.id, status='Pending').all()

    # Fetch sent requests (from this influencer to sponsors)
    sent_requests = Requesttt.query.filter_by(influencer_id=current_user.id).all()

    accepted_requests = Request.query.filter_by(influencer_id=current_user.id, status='Accepted').all()

    incoming_requests_count = len(pending_requests)
    sent_requests_count = len(sent_requests)
    accepted_requests_count = len(accepted_requests)

    # Generate the graph for influencer stats
    generate_influencer_stats_graph(incoming_requests_count, sent_requests_count, accepted_requests_count)

    return render_template('influstats.html', 
                           incoming_requests_count=incoming_requests_count,
                           sent_requests_count=sent_requests_count,
                           accepted_requests_count=accepted_requests_count)
                           
def generate_influencer_stats_graph(incoming_requests, sent_requests, accepted_requests):
    categories = ['Incoming Requests', 'Sent Requests', 'Accepted Requests']
    values = [incoming_requests, sent_requests, accepted_requests]

    plt.figure(figsize=(8, 5))
    plt.bar(categories, values, color=['blue', 'orange', 'green'])
    plt.xlabel('Categories', fontsize=16)
    plt.ylabel('Counts', fontsize=16)
    plt.title('Influencer Overview')

    # Save the figure
    chart_path = os.path.join('static', 'influstats_chart.png')
    plt.savefig(chart_path)
    plt.close()

@app.route('/rate_influencer/<int:user_id>', methods=['POST'])
@login_required
def rate_influencer(user_id):
    influencer = Influencer.query.filter_by(user_id=user_id).first()
    if not influencer:
        flash('Influencer not found.', 'error')
        return redirect(url_for('profile_view', user_id=user_id))

    rating_value = request.form.get('rating')
    if not rating_value:
        flash('Please provide a rating.', 'error')
        return redirect(url_for('profile_view', user_id=user_id))

    rating_value = int(rating_value)
    if rating_value < 1 or rating_value > 5:
        flash('Rating must be between 1 and 5.', 'error')
        return redirect(url_for('profile_view', user_id=user_id))

    # Check if the user has already rated this influencer
    existing_rating = Rating.query.filter_by(user_id=current_user.id, influencer_id=influencer.id).first()
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating_value
        flash('Rating updated successfully!', 'success')
    else:
        # Create a new rating
        new_rating = Rating(user_id=current_user.id, influencer_id=influencer.id, rating=rating_value)
        db.session.add(new_rating)
        flash('Rating submitted successfully!', 'success')

    # Update the influencer's overall rating
    ratings = Rating.query.filter_by(influencer_id=influencer.id).all()
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        influencer.rating = round(avg_rating, 2)
        influencer.reach = len(ratings)
    else:
        influencer.rating = 0.00  # Set to 0.00 if no ratings
    influencer.reach = len(ratings)
    db.session.commit()

    return redirect(url_for('profile_view', user_id=user_id))


@app.route('/sponsordash')
@login_required
def sponsordash():
    if current_user.user_type != 'sponsor':
        flash('Access denied. You must be a sponsor to view this page.', 'error')
        return redirect(url_for('index'))

    # Fetch requests from influencers to this sponsor
    influencer_requests = Requesttt.query.filter_by(sponsor_id=current_user.id).all()

    # Fetch sent requests (from this sponsor to influencers)
    sent_requests = Request.query.filter_by(sponsor_id=current_user.id).all()

    return render_template('sponsordash.html', 
                           current_user=current_user, 
                           influencer_requests=influencer_requests, 
                           sent_requests=sent_requests)

@app.route('/accept_requesttt/<int:request_id>', methods=['POST'])
@login_required
def accept_requesttt(request_id):
    request = Requesttt.query.get(request_id)  # Fetch the request by ID
    if request:
        if request.status == 'Pending':  # Check if the request is currently pending
            request.status = 'Accepted'  # Change status to Accepted
            db.session.commit()  # Commit the changes to the database
            flash('Request has been accepted successfully.', 'success')
        else:
            flash('Request is not pending.', 'info')  # Inform that it's not pending
    else:
        flash('Request not found.', 'error')  # Handle case where request is not found
    return redirect(url_for('sponsordash'))  # Redirect back to the sponsor dashboard

@app.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    request = Request.query.get(request_id)  # Fetch the request by ID
    if request:
        if request.status == 'Pending':  # Check if the request is currently pending
            request.status = 'Accepted'  # Change status to Accepted
            db.session.commit()  # Commit the changes to the database
            flash('Request has been accepted successfully.', 'success')
        else:
            flash('Request is not pending.', 'info')  # Inform that it's not pending
    else:
        flash('Request not found.', 'error')  # Handle case where request is not found
    return redirect(url_for('influencerdash'))  # Redirect back to the influencer dashboard

@app.route('/reject_requesttt/<int:request_id>', methods=['POST'])
@login_required
def reject_requesttt(request_id):
    request = Requesttt.query.get(request_id)  # Fetch the request by ID
    if request:
        if request.status == 'Pending':  # Check if the request is currently pending
            request.status = 'Rejected'  # Change status to Rejected
            db.session.commit()  # Commit the changes to the database
            flash('Request has been rejected successfully.', 'success')
        else:
            flash('Request is not pending.', 'info')  # Inform that it's not pending
    else:
        flash('Request not found.', 'error')  # Handle case where request is not found
    return redirect(url_for('sponsordash'))  # Redirect back to the sponsor dashboard

@app.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    request = Request.query.get(request_id)  # Fetch the request by ID
    if request:
        if request.status == 'Pending':  # Check if the request is currently pending
            request.status = 'Rejected'  # Change status to Rejected
            db.session.commit()  # Commit the changes to the database
            flash('Request has been rejected successfully.', 'success')
        else:
            flash('Request is not pending.', 'info')  # Inform that it's not pending
    else:
        flash('Request not found.', 'error')  # Handle case where request is not found
    return redirect(url_for('influencerdash'))  # Redirect back to the influencer dashboard


@app.route('/negotiate_request', methods=['POST'])
@login_required
def negotiate_request():
    request_id = request.form.get('request_id')
    amount = request.form.get('amount')

    # Assuming you have a way to determine if it's a Request or Requesttt
    # For example, you might pass an additional parameter to identify the type
    request_type = request.form.get('request_type')  # 'request' or 'requesttt'

    if request_type == 'request':
        request_entry = Request.query.get(request_id)
    else:
        request_entry = Requesttt.query.get(request_id)

    if request_entry:
        request_entry.negotiation = float(amount)  # Store the negotiated amount
        db.session.commit()
        flash('Negotiation submitted successfully!', 'success')
    else:
        flash('Request not found.', 'error')

    return redirect(url_for('influencerdash'))  # Redirect back to the influencer dashboard


@app.route('/campaigns', methods=['GET', 'POST'])
@login_required
def campaigns():
    if request.method == 'POST':
        name = request.form['name']
        budget = request.form['budget']
        description = request.form['description']
        goal = request.form['goal']
        visibility = request.form['visibility']

        # Create and save a new campaign
        new_campaign = Campaign(
            name=name,
            budget=budget,
            description=description,
            goal=goal,
            visibility=visibility,
            user_id=current_user.id
        )
        db.session.add(new_campaign)
        db.session.commit()

        flash('Campaign added successfully!', 'success')
        return redirect(url_for('campaigns'))

    user_campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    return render_template('campaigns.html', campaigns=user_campaigns)

@app.route('/addcampaigns', methods=['GET', 'POST'])
@login_required
def addcampaigns():
    if request.method == 'POST':
        name = request.form.get('name')
        budget = float(request.form.get('budget'))
        description = request.form.get('description')
        goal = request.form.get('goal')
        visibility = request.form.get('visibility')

        new_campaign = Campaign(
            name=name,
            budget=budget,
            description=description,
            goal=goal,
            visibility=visibility,
            user_id=current_user.id
        )

        db.session.add(new_campaign)
        db.session.commit()

        flash('Campaign added successfully!', 'success')
        return redirect(url_for('campaigns'))

    return render_template('addcampaigns.html')

@app.route('/update_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
def update_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)  # Fetch the campaign by ID

    if request.method == 'POST':
        # Get updated data from the form
        campaign.name = request.form.get('name')
        campaign.budget = request.form.get('budget')
        campaign.description = request.form.get('description')
        campaign.goal = request.form.get('goal')
        campaign.visibility = request.form.get('visibility')

        db.session.commit()  # Commit the changes to the database
        flash('Campaign updated successfully!', 'success')
        return redirect(url_for('campaigns'))  # Redirect to the campaigns page

    return render_template('update_campaign.html', campaign=campaign)  # Render the update form

@app.route('/delete_campaign/<int:campaign_id>', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        flash('You do not have permission to delete this campaign.', 'error')
        return redirect(url_for('campaigns'))

    db.session.delete(campaign)
    db.session.commit()

    flash('Campaign deleted successfully!', 'success')
    return redirect(url_for('campaigns'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        search_type = request.form['type']
        query = request.form['query']
        if search_type == 'influencer':
            results = User.query.filter(User.user_type == 'influencer', User.name.contains(query)).all()
        else:
            results = User.query.filter(User.user_type == 'sponsor', User.name.contains(query)).all()
    else:
        results = User.query.filter(User.user_type != 'admin').all()
        search_type = ''
        query = ''
    return render_template('search.html', results=results, query=query, search_type=search_type)

@app.route('/stats')
@login_required
def stats():
    if current_user.user_type != 'sponsor':
        flash('Access denied. You must be a sponsor to view this page.', 'error')
        return redirect(url_for('index'))

    # Fetch sent requests (from this sponsor to influencers)
    sent_requests = Request.query.filter_by(sponsor_id=current_user.id).all()
    sent_requests_count = len(sent_requests)

    # Fetch incoming requests (from influencers to this sponsor)
    incoming_requests = Requesttt.query.filter_by(sponsor_id=current_user.id).all()
    incoming_requests_count = len(incoming_requests)

    # Get the last request ID (serial number)
    last_request_id = sent_requests[-1].id if sent_requests else None  # Get the last sent request ID

    # Count public and private campaigns
    public_campaigns_count = Campaign.query.filter_by(user_id=current_user.id, visibility='public').count()
    private_campaigns_count = Campaign.query.filter_by(user_id=current_user.id, visibility='private').count()

    generate_stats_graph(sent_requests_count, incoming_requests_count, public_campaigns_count, private_campaigns_count)

    return render_template('stats.html', 
                           sent_requests_count=sent_requests_count,
                           incoming_requests_count=incoming_requests_count,
                           last_request_id=last_request_id,
                           public_campaigns_count=public_campaigns_count,
                           private_campaigns_count=private_campaigns_count)

def generate_stats_graph(sent_requests, incoming_requests, public_campaigns, private_campaigns):
    categories = ['Sent Requests', 'Incoming Requests', 'Public Campaigns', 'Private Campaigns']
    values = [sent_requests, incoming_requests, public_campaigns, private_campaigns]

    plt.figure(figsize=(8, 5))
    plt.bar(categories, values, color=['blue', 'orange', 'green', 'red'])
    plt.xlabel('Categories', fontsize=16)
    plt.ylabel('Counts', fontsize=16)
    plt.title('Overview')

    # Save the figure
    chart_path = os.path.join('static', 'stats_chart.png')
    plt.savefig(chart_path)
    plt.close()

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/profile/<int:user_id>')
def profile_view(user_id):
    user = User.query.get(user_id)  # Function to get user details
    if user.user_type == 'sponsor':
        user.campaigns = Campaign.query.filter_by(user_id=user_id).filter(Campaign.status != 'Flagged').all()  # Get campaigns that are not flagged
        
    return render_template('profile_view.html', user=user)

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('influencerdash'))

    file = request.files['image']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('influencerdash'))

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        influencer = Influencer.query.filter_by(user_id=current_user.id).first()
        if influencer:
            influencer.image = filename
            db.session.commit()

        flash('Image uploaded successfully', 'success')
        return redirect(url_for('influencerdash'))

@app.route('/send_request/<int:user_id>', methods=['POST'])
@login_required
def send_request(user_id):
    campaign_task = request.form.get('campaign_task')
    message = request.form.get('message')
    payment_amount = request.form.get('askedAmount')
    campaign_id = request.form.get('campaign')

    try:
        if current_user.user_type == 'sponsor':
            # Sponsor sending request to influencer
            campaign = Campaign.query.get(campaign_id)
            new_request = Request(
                campaign_task=campaign_task,
                message=message,
                payment_amount=float(payment_amount),
                sponsor_id=current_user.id,
                influencer_id=user_id,
                status='Pending',
                campaign_name=campaign.name if campaign else ''
            )
        else:
            # Influencer sending request to sponsor
            campaign = Campaign.query.get(campaign_id)
            new_request = Requesttt(
                campaign_task=campaign_task,
                message=message,
                payment_amount=float(payment_amount),
                influencer_id=current_user.id,
                sponsor_id=user_id,
                status='Pending',
                campaign_name=campaign.name if campaign else ''
            )

        db.session.add(new_request)
        db.session.commit()
        flash('Request sent successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to send request. Please try again. Error: {str(e)}', 'error')

    return redirect(url_for('profile_view', user_id=user_id))

@app.route('/influnegotiate', methods=['GET'])
@login_required
def influnegotiate():
    request_id = request.args.get('request_id')
    # Logic to handle the negotiation for the specific request
    return render_template('influnegotiate.html', request_id=request_id)

@app.route('/accept_negotiation', methods=['POST'])
@login_required
def accept_negotiation():
    request_id = request.form.get('request_id')
    request_type = request.form.get('request_type')  # 'request' or 'requesttt'

    if request_type == 'request':
        request_entry = Request.query.get(request_id)
    else:
        request_entry = Requesttt.query.get(request_id)

    if request_entry:
        # Check if the negotiation amount is not None or 'N/A'
        if request_entry.negotiation is not None and request_entry.negotiation != 'N/A':
            # Update the payment amount to the negotiated amount
            request_entry.payment_amount = request_entry.negotiation
            db.session.commit()
            flash('Negotiation accepted successfully!', 'success')
        else:
            flash('Negotiation amount is not valid.', 'error')  # Handle case where negotiation is invalid
    else:
        flash('Request not found.', 'error')

    return redirect(url_for('influencerdash'))  # Redirect back to the sponsor dashboard

@app.route('/negotiate_requesttt', methods=['POST'])
@login_required
def negotiate_requesttt():
    request_id = request.form.get('request_id')
    amount = request.form.get('amount')

    # Identify the request entry in the Requesttt table
    request_entry = Requesttt.query.get(request_id)

    if request_entry:
        request_entry.negotiation = float(amount)  # Store the negotiated amount
        db.session.commit()
        flash('Negotiation submitted successfully!', 'success')
    else:
        flash('Request not found.', 'error')

    return redirect(url_for('sponsordash'))  # Redirect back to the sponsor dashboard

@app.route('/accept_negotiationtt', methods=['POST'])
@login_required
def accept_negotiationtt():
    request_id = request.form.get('request_id')

    # Get the request entry from the Requesttt table
    request_entry = Request.query.get(request_id)

    if request_entry:
        # Check if the negotiation amount is not None or 'N/A'
        if request_entry.negotiation is not None and request_entry.negotiation != 'N/A':
            # Update the payment amount to the negotiated amount
            request_entry.payment_amount = request_entry.negotiation
            db.session.commit()
            flash('Negotiation accepted successfully!', 'success')
        else:
            flash('Negotiation amount is not valid.', 'error')  # Handle case where negotiation is invalid
    else:
        flash('Request not found.', 'error')

    return redirect(url_for('sponsordash'))  # Redirect back to the sponsor dashboard

@app.route('/sponsornegotiate', methods=['GET'])
@login_required
def sponsornegotiate():
    request_id = request.args.get('request_id')
    # Logic to handle the negotiation for the specific request
    return render_template('sponsornegotiate.html', request_id=request_id)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)