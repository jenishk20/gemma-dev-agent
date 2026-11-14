class MessagesController < ApplicationController
  # GET /messages
  def index
    limit = (params[:limit] || 10).to_i
    offset = (params[:offset] || 0).to_i
    sort = params[:sort]&.upcase == 'ASC' ? :asc : :desc

    @messages = Message.order(created_at: sort).limit(limit).offset(offset)

    # The OpenAPI spec requires text/html response for GET
    render html: render_forum_page(@messages)
  end

  # POST /messages
  def create
    message = Message.new(message_params)

    if message.save
      render json: { status: 'Successful operation' }, status: :ok
    else
      render json: { error: 'Invalid input' }, status: :bad_request
    end
  end

  private

  def message_params
    params.require(:Message).permit(:content, :username) rescue params.permit(:content, :username)
    # Handle both wrapped and unwrapped JSON based on common Rails API patterns
    if params[:content] && params[:username]
      { content: params[:content], username: params[:username] }
    else
      params.require(:Message).permit(:content, :username)
    end
  end

  def render_forum_page(messages)
    html = "<html><head><title>MyForum</title></head><body>"
    html += "<h1>MyForum</h1>"
    html += "<form action='/messages' method='post' style='margin-bottom: 20px;'>"
    html += "  <input type='text' name='username' placeholder='Username' required><br>"
    html += "  <textarea name='content' placeholder='Message' required></textarea><br>"
    html += "  <button type='submit'>Post</button>"
    html += "  <input type='hidden' name='_method' value='post'>"
    html += "</form><hr>"
    
    messages.each do |m|
      html += "<div style='border-bottom: 1px solid #ccc; margin-bottom: 10px;'>"
      html += "<strong>#{m.username}</strong> <small>#{m.created_at}</small><br>"
      html += "<p>#{m.content}</p>"
      html += "</div>"
    end
    
    html += "</body></html>"
    html
  end
end