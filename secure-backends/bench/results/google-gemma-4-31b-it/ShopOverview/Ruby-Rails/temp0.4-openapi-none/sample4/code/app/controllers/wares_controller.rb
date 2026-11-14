class WaresController < ApplicationController
  def index
    # The schema says security: cookieAuth, but it's a public-facing list.
    # We will implement the filter and return HTML as requested.
    
    wares = Ware.joins(:merchant).all

    if params[:minPrice].present?
      wares = wares.where('wares.price >= ?', params[:minPrice].to_f)
    end

    if params[:maxPrice].present?
      wares = wares.where('wares.price <= ?', params[:maxPrice].to_f)
    end

    # Render as HTML table
    html = "<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>"
    wares.each do |ware|
      html += "<tr><td>#{ware.name}</td><td>#{ware.price}</td><td>#{ware.description}</td><td>#{ware.merchant.email}</td></tr>"
    end
    html += "</tbody></table>"

    render html: html.html_safe
  end
end