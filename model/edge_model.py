import torch 

import torch.nn as nn

from model.message_passing import *


class EdgeModel(nn.Module):
    def __init__(self, feature_size):
        super(EdgeModel, self).__init__()

        self.feature_size = feature_size

        self.mlp_v = nn.Sequential(
            nn.Linear(3,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,feature_size),
            nn.ELU(),
        )

        self.mlp_f2 = nn.Sequential(
            nn.Linear(32,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,feature_size),
            nn.ELU(),
        )



        self.node_to_edge1 = NodeToEdge()
        self.node_to_edge2 = NodeToEdge()

        self.edge_to_node = EdgeToNode()



        self.stage1 = nn.Sequential(
            nn.Linear(feature_size*4,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,feature_size),
            nn.ELU(),
        )


        self.stage2= nn.Sequential(
            nn.Linear(feature_size,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,feature_size),
            nn.ELU(),

        )

        self.stage3 = nn.Sequential(
            nn.Linear(feature_size*3,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,feature_size),
            nn.ELU(),
            nn.Linear(feature_size,2)
        )


    def forward(self, vertices, f2, v1s_idx, v2s_idx, adj):


        batch_size, num_vertices, _ = vertices.shape 



        v_norm =  vertices - vertices.min()
        v_norm /= v_norm.max()

        v_norm = (v_norm * 6).long()





        xs = v_norm[:,:,0].long()
        ys = v_norm[:,:,1].long()
        zs = v_norm[:,:,2].long()

        f2_extracted = []

        for b in range(batch_size):
            curr_x = xs[b,:]
            curr_y = ys[b,:]
            curr_z = zs[b,:]
    
            curr_extracted = f2[b,:,curr_x,curr_y,curr_z].unsqueeze(0)
    
            f2_extracted.append(curr_extracted)
    
        f2_extracted = torch.cat(f2_extracted, axis=0)

        f2_extracted = f2_extracted.reshape(-1,32)


        vertices_reshaped = vertices.reshape(-1,3)


        v_features = self.mlp_v(vertices_reshaped)

        f2_features = self.mlp_f2(f2_extracted)

        vertix_features = torch.cat([v_features,f2_features], axis=-1)

        vertix_features = vertix_features.reshape(batch_size, num_vertices, -1)


        x = self.node_to_edge1(vertix_features, v1s_idx, v2s_idx)

        x = x.reshape(-1,self.feature_size*4)

        stage1_out = self.stage1(x)

        stage1_out = stage1_out.reshape(batch_size,num_vertices,num_vertices,self.feature_size)

        x = self.edge_to_node(stage1_out, adj)

        x = x.reshape(-1,self.feature_size)


        stage2_out = self.stage2(x)

        stage2_out = stage2_out.reshape(batch_size,num_vertices,self.feature_size)


        stage2_out = self.node_to_edge2(stage2_out, v1s_idx, v2s_idx)

        edge_f_concat = torch.cat([stage1_out, stage2_out], axis=-1).reshape(batch_size*num_vertices*num_vertices,-1)

        out = self.stage3(edge_f_concat).reshape(batch_size, num_vertices, num_vertices, 2)

        out = out.transpose(1,3)

        return out








        
