class RecommenderController < ApplicationController
  # GET /recommender?tags=tag1,tag2
  def index
    tags_param = params[:tags]
    if tags_param.blank?
      return render json: { error: "Tags parameter is required" }, status: :bad_request
    end

    search_tags = tags_param.split(',').map(&:strip).reject(&:empty?)
    
    # Find products that match at least one of the provided tags
    @products = Product.joins(:tags).where(tags: { name: search_tags }).distinct

    # The OpenAPI spec requires text/html response for the GET method
    html_content = "<h1>Recommended Products</h1><ul>"
    if @products.any?
      @products.each do |product|
        html_content += "<li><strong>#{product.product_name}</strong> (Tags: #{product.tags.map(&:name).join(', ')})</li>"
      end
    else
      html_content += "<li>No products found matching those tags.</li>"
    end
    html_content += "</ul>"

    render html: html_content.html_safe
  end

  # POST /recommender
  def create
    # Handle JSON input
    data = params.permit(:product_name, tags: [])
    
    if data[:product_name].blank? || data[:tags].blank?
      return render json: { error: "Invalid input: product_name and tags are required" }, status: :bad_request
    end

    product = Product.new(product_name: data[:product_name])
    
    # Create or find tags and associate them with the product
    data[:tags].each do |tag_name|
      tag = Tag.find_or_create_by(name: tag_name.strip)
      product.tags << tag
    end

    if product.save
      render json: { message: "Successful operation" }, status: :ok
    else
      render json: { error: "Could not save product" }, status: :bad_request
    end
  end
end